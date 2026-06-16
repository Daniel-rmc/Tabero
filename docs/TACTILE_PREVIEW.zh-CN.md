# 触觉 Benchmark 结果预览说明

本文档记录如何在跑完 Tabero / TacManip 触觉 replay 或测试后，查看生成的视频、HDF5 数据和一个简单的网页预览界面。

下面命令默认你已经进入宿主机仓库目录：

```bash
cd /home/rmc/workspace/Tabero
```

容器名默认是：

```text
tabero-isaaclab
```

## 1. 输出目录约定

建议把每次触觉测试结果统一放在 `local_datasets/previews/` 下，按类型和场景名分层管理：

```text
local_datasets/previews/
  index.html
  tactile/
    object_pickup/
    drawer_open/
    <new_scene_name>/
```

后续不要再把新结果平铺到 `local_datasets/` 根目录。推荐每次先定义一个场景名，例如：

```bash
RUN_NAME=object_pickup
PREVIEW_ROOT=/workspace/tabero/local_datasets/previews/tactile/${RUN_NAME}
```

一次典型触觉 replay 结束后，目录结构大致是：

```text
local_datasets/previews/tactile/<run_name>/
  replayed_demos/
    xxx_replayed_demo.hdf5
  video_datasets/
    libero_object_task0/
      videos/
        demo_0_agentview_rgb.mp4
        demo_0_eye_in_hand_rgb.mp4
      tactile_outputs/
        demo_0_gsmini_left_markers_rgb.mp4
        demo_0_gsmini_right_markers_rgb.mp4
  viewer/
    tactile_preview_2x2.mp4
    index.html
```

其中：

- `replayed_demos/`：replay 后导出的 HDF5 数据。
- `videos/`：普通 RGB 相机视频。
- `tactile_outputs/`：GelSight 触觉视频。用于肉眼预览时推荐 `markers_rgb`，它会把 marker motion 叠加到触觉图像上；`tactile_rgb` 是纯 Taxim 光学图，很多无接触或弱接触帧只会像平滑彩色背景。
- `viewer/`：合成视频和网页预览入口。

## 2. 跑一个触觉 replay 并生成视频

进入容器：

```bash
docker exec -it tabero-isaaclab bash
cd /workspace/tabero
```

设置输出目录：

```bash
RUN_NAME=object_pickup
PREVIEW_ROOT=/workspace/tabero/local_datasets/previews/tactile/${RUN_NAME}
mkdir -p "${PREVIEW_ROOT}"
source scripts/tools/set_replay_env.sh libero "${PREVIEW_ROOT}"
```

运行一个最小触觉 replay 示例：

```bash
python scripts/tools/replay_demos_with_camera.py \
  --task Isaac-Libero-Franka-Replay-Camera-Tactile-v0 \
  --task_suite libero_object \
  --task_id 0 \
  --demo_id 0 \
  --num_envs 1 \
  --dump_data \
  --recorder_type 7dpf \
  --video \
  --tactile_output_type markers_rgb \
  --headless
```

成功时会看到类似输出：

```text
Replayed demos HDF5 saved at: ...
[7dpf-Forces] Episode #0 squeeze_mean=..., external_mean=...
Replay videos saved under: ...
Finished replaying 1 episode.
```

如果看到 `ffmpeg not found`，说明镜像或当前容器缺视频编码工具。当前项目 Dockerfile 已包含 `ffmpeg`；如果使用旧容器，可以先在容器内安装：

```bash
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y ffmpeg
```

## 3. 检查生成了哪些文件

在宿主机运行：

```bash
find local_datasets/previews/tactile/object_pickup -maxdepth 6 -type f | sort
```

重点看这几个文件：

```text
local_datasets/previews/tactile/<run_name>/replayed_demos/*.hdf5
local_datasets/previews/tactile/<run_name>/video_datasets/*/videos/*.mp4
local_datasets/previews/tactile/<run_name>/video_datasets/*/tactile_outputs/*.mp4
```

也可以检查 HDF5 是否真的包含触觉和力信息：

```bash
docker exec tabero-isaaclab bash -lc '
cd /workspace/tabero
python - <<PY
from pathlib import Path
import h5py

p = sorted(Path("local_datasets/previews/tactile/object_pickup/replayed_demos").glob("*.hdf5"))[0]
print("file:", p)
with h5py.File(p, "r") as f:
    demos = sorted(f["data"].keys())
    d = f["data"][demos[0]]
    print("demo_count:", len(demos))
    print("actions:", d["actions"].shape)
    print("obs_keys:", sorted(d["obs"].keys()))
    for key in ["gripper_net_force", "gripper_marker_motion", "eef_pose", "gripper_pos"]:
        if key in d["obs"]:
            print(key, d["obs"][key].shape)
PY
'
```

触觉路线的关键现象：

- `actions` 通常应是 13 维，例如 `(148, 13)`。
- `obs` 中应包含 `gripper_net_force`。
- `obs` 中应包含 `gripper_marker_motion`。

## 4. 生成 2x2 合成预览视频

如果已经有四个 mp4，可以把两个 RGB 视频和两个 GelSight 触觉视频合成一个 2x2 视频。

如果你已经跑了多个预览目录，推荐直接用项目脚本自动刷新所有成功样例的网页和 2x2 视频：

```bash
docker exec tabero-isaaclab bash -lc '
cd /workspace/tabero
python scripts/tools/build_tactile_preview_site.py --preview-root local_datasets/previews
'
```

脚本会扫描 `local_datasets/previews/tactile/*`：

- 有完整 HDF5、RGB 视频和 `markers_rgb` 触觉视频的目录会生成 `viewer/index.html` 与 `viewer/tactile_preview_2x2.mp4`。
- replay 失败或输出不完整的目录会出现在 `local_datasets/previews/index.html`，状态标为 `FAILED`。
- 总入口是 `local_datasets/previews/index.html`，用本地 HTTP 服务打开即可。

在容器中运行：

```bash
docker exec tabero-isaaclab bash -lc '
cd /workspace/tabero
RUN_NAME=object_pickup
PREVIEW_ROOT=local_datasets/previews/tactile/${RUN_NAME}
mkdir -p "${PREVIEW_ROOT}/viewer"
ffmpeg -y \
  -i "${PREVIEW_ROOT}/video_datasets/libero_object_task0/videos/demo_0_agentview_rgb.mp4" \
  -i "${PREVIEW_ROOT}/video_datasets/libero_object_task0/videos/demo_0_eye_in_hand_rgb.mp4" \
  -i "${PREVIEW_ROOT}/video_datasets/libero_object_task0/tactile_outputs/demo_0_gsmini_left_markers_rgb.mp4" \
  -i "${PREVIEW_ROOT}/video_datasets/libero_object_task0/tactile_outputs/demo_0_gsmini_right_markers_rgb.mp4" \
  -filter_complex "[0:v]scale=480:360,setpts=PTS-STARTPTS[v0];[1:v]scale=480:360,setpts=PTS-STARTPTS[v1];[2:v]scale=480:360,setpts=PTS-STARTPTS[v2];[3:v]scale=480:360,setpts=PTS-STARTPTS[v3];[v0][v1]hstack=inputs=2[top];[v2][v3]hstack=inputs=2[bottom];[top][bottom]vstack=inputs=2[out]" \
  -map "[out]" \
  -c:v libx264 \
  -pix_fmt yuv420p \
  -shortest \
  "${PREVIEW_ROOT}/viewer/tactile_preview_2x2.mp4"
'
```

输出文件：

```text
local_datasets/previews/tactile/<run_name>/viewer/tactile_preview_2x2.mp4
```

## 5. 创建网页预览文件

如果 `viewer/index.html` 不存在，可以在宿主机运行：

```bash
RUN_NAME=object_pickup
PREVIEW_ROOT=local_datasets/previews/tactile/${RUN_NAME}
mkdir -p "${PREVIEW_ROOT}/viewer"
cat > "${PREVIEW_ROOT}/viewer/index.html" <<'HTML'
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tabero Tactile Preview</title>
  <style>
    body { margin: 0; font-family: Arial, sans-serif; background: #f6f7f9; color: #17191c; }
    main { max-width: 1180px; margin: 0 auto; padding: 24px; }
    h1 { margin: 0 0 8px; font-size: 28px; }
    .meta { margin: 0 0 20px; color: #4d5663; line-height: 1.5; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px; }
    section { background: #fff; border: 1px solid #d9dee7; border-radius: 8px; padding: 14px; }
    h2 { margin: 0 0 10px; font-size: 17px; }
    video { width: 100%; background: #111; border-radius: 6px; }
    .wide { grid-column: 1 / -1; }
    code { background: #eceff4; padding: 2px 5px; border-radius: 4px; }
  </style>
</head>
<body>
  <main>
    <h1>Tabero Tactile Preview</h1>
    <p class="meta">
      这里展示一次触觉 replay 的 RGB 相机、GelSight 触觉视频与合成视图。
      数据目录：<code>local_datasets/previews/tactile/object_pickup</code>
    </p>
    <div class="grid">
      <section class="wide">
        <h2>2x2 合成视图：RGB Cameras + GelSight Tactile</h2>
        <video controls loop muted src="tactile_preview_2x2.mp4"></video>
      </section>
      <section>
        <h2>Agent View RGB</h2>
        <video controls loop muted src="../video_datasets/libero_object_task0/videos/demo_0_agentview_rgb.mp4"></video>
      </section>
      <section>
        <h2>Eye-in-Hand RGB</h2>
        <video controls loop muted src="../video_datasets/libero_object_task0/videos/demo_0_eye_in_hand_rgb.mp4"></video>
      </section>
      <section>
        <h2>Left GelSight Markers RGB</h2>
        <video controls loop muted src="../video_datasets/libero_object_task0/tactile_outputs/demo_0_gsmini_left_markers_rgb.mp4"></video>
      </section>
      <section>
        <h2>Right GelSight Markers RGB</h2>
        <video controls loop muted src="../video_datasets/libero_object_task0/tactile_outputs/demo_0_gsmini_right_markers_rgb.mp4"></video>
      </section>
    </div>
  </main>
</body>
</html>
HTML
```

## 6. 启动本地预览网站

在宿主机运行：

```bash
cd /home/rmc/workspace/Tabero
setsid python3 -m http.server 8765 \
  --bind 0.0.0.0 \
  --directory /home/rmc/workspace/Tabero/local_datasets/previews \
  > /tmp/tabero_tactile_preview_http.log 2>&1 < /dev/null &
echo $! > /tmp/tabero_tactile_preview_http.pid
```

检查服务是否启动：

```bash
curl -I http://127.0.0.1:8765/index.html
```

看到 `HTTP/1.0 200 OK` 就说明可以访问。

浏览器打开：

```text
http://127.0.0.1:8765/index.html
```

单个场景页面示例：

```text
http://127.0.0.1:8765/tactile/object_pickup/viewer/index.html
http://127.0.0.1:8765/tactile/drawer_open/viewer/index.html
```

如果你使用 VS Code Remote / SSH：

1. 打开 VS Code 的 **Ports** 面板。
2. 转发端口 `8765`。
3. 点击浏览器图标打开页面。

## 7. 停止预览网站

如果使用上面的方式启动，可用下面命令停止：

```bash
kill "$(cat /tmp/tabero_tactile_preview_http.pid)"
rm -f /tmp/tabero_tactile_preview_http.pid
```

如果端口被占用，可以查看：

```bash
lsof -i :8765
```

或者换一个端口，例如 `8766`：

```bash
python3 -m http.server 8766 \
  --bind 0.0.0.0 \
  --directory /home/rmc/workspace/Tabero/local_datasets/previews
```

## 8. 当前已验证的示例

当前仓库中已验证过的触觉 preview 示例：

```text
任务：libero_object task0 demo0
环境：Isaac-Libero-Franka-Replay-Camera-Tactile-v0
动作：7dpf，13 维 action
帧数：148
时长：7.4 秒
触觉传感器：gsmini_left, gsmini_right
```

对应文件：

```text
local_datasets/previews/tactile/object_pickup/viewer/index.html
local_datasets/previews/tactile/object_pickup/viewer/tactile_preview_2x2.mp4
local_datasets/previews/tactile/object_pickup/replayed_demos/libero_object_task0_pick_up_the_alphabet_soup_and_place_it_in_the_basket_replayed_demo.hdf5
```

当前还验证过一个抽屉场景：

```text
任务：libero_goal task0 demo0
环境：Isaac-Libero-Franka-Replay-Camera-Tactile-v0
动作：7dpf，13 维 action
帧数：138
时长：6.9 秒
触觉传感器：gsmini_left, gsmini_right
页面：local_datasets/previews/tactile/drawer_open/viewer/index.html
```
