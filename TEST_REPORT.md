# Tabero Docker 复现测试报告

生成日期：2026-06-10

## 复现目标

将 `NathanWu7/Tabero` fork 到个人仓库，并补齐基于 Docker 的 Isaac Sim / Isaac Lab 复现环境，使后续可以直接在容器内继续做 Tabero 论文相关研究改进。

Fork 状态：

- 上游仓库：`git@github.com:NathanWu7/Tabero.git`
- 个人 fork：`git@github.com:Daniel-rmc/Tabero.git`
- 本地路径：`/home/rmc/workspace/Tabero`

## Docker 环境

本次复现使用 NVIDIA 官方 Isaac Lab 容器作为基础镜像：

- 基础镜像：`nvcr.io/nvidia/isaac-lab:2.3.2`
- 容器镜像名：`tabero-isaaclab:latest`
- Compose service：`tabero`
- 容器内项目路径：`/workspace/tabero`
- GPU：通过 Docker Compose 请求全部 NVIDIA GPU

参考官方文档：

- Isaac Lab Docker 部署文档：https://isaac-sim.github.io/IsaacLab/main/source/deployment/docker.html
- Isaac Sim 容器安装文档：https://docs.isaacsim.omniverse.nvidia.com/5.0.0/installation/install_container.html

主要环境修复：

- 将模板式 Docker 配置改为 Tabero 项目配置。
- 将无效的 `COPY ../` 改为以仓库根目录为 build context 的 `COPY . /workspace/tabero`。
- 安装 `source/tac_manip` 与 `benchmarks/openpi/openpi-client` 两个 editable 包。
- 补齐运行样例测试所需依赖：`pytest`、`tyro`、`h5py`、`opencv-python-headless`、`tqdm`、`matplotlib`。
- 增加 `python/python3/pip/pip3` wrapper，固定使用 Isaac Sim 自带 Python。
- 增加 Isaac/Omniverse 常用 cache volume，避免重复启动时缓存完全丢失。
- 修复根目录 `pyproject.toml` 缺逗号导致 pytest 无法读取配置的问题。
- 修复 `scripts/list_envs.py` 仍筛选模板任务的问题，使其列出 Tabero 注册环境。

## 使用命令

构建镜像：

```bash
docker compose --env-file docker/.env.base -f docker/docker-compose.yaml build tabero
```

进入容器：

```bash
docker compose --env-file docker/.env.base -f docker/docker-compose.yaml run --rm tabero
```

运行 OpenPI client 单元测试：

```bash
docker compose --env-file docker/.env.base -f docker/docker-compose.yaml run --rm tabero -lc \
  'python -m pytest -q benchmarks/openpi/openpi-client/src/openpi_client'
```

启动一个长期运行的复现容器，便于后续研究直接进入同一环境：

```bash
docker compose --env-file docker/.env.base -f docker/docker-compose.yaml up -d tabero
docker exec -it tabero-isaaclab bash
```

本次已在宿主机下载完整数据到仓库本地 `local_datasets/`，该目录已加入忽略规则，不会进入 Git 或 Docker build context：

```bash
unset HF_ENDPOINT
hf download NathanWu7/Isaaclab_Libero \
  --repo-type dataset \
  --local-dir local_datasets/Isaaclab_Libero

hf download china-sae-robotics/Tactile_Manipulation_Dataset \
  --repo-type dataset \
  --local-dir local_datasets/Tactile_Manipulation_Dataset
```

当前数据链接使用相对 symlink，宿主机和容器内都可解析：

```bash
ln -sfn ../../../local_datasets/Isaaclab_Libero/assembled_hdf5 benchmarks/datasets/libero/assembled_hdf5
ln -sfn ../../../local_datasets/Isaaclab_Libero/replayed_demos benchmarks/datasets/libero/replayed_demos
ln -sfn ../../../local_datasets/Isaaclab_Libero/video_datasets benchmarks/datasets/libero/video_datasets
ln -sfn ../../../local_datasets/Isaaclab_Libero/USD benchmarks/datasets/libero/USD
ln -sfn ../../../local_datasets/Isaaclab_Libero/lerobot_task_space benchmarks/datasets/libero/lerobot_task_space
ln -sfn ../../../../local_datasets/Tactile_Manipulation_Dataset/assets/data source/tac_manip/tac_manip/assets/data
```

注意：`find` 默认不跟随目录 symlink，验证数据量时应使用 `find -L`。

列出 Tabero Isaac Lab 环境：

```bash
docker compose --env-file docker/.env.base -f docker/docker-compose.yaml run --rm tabero -lc \
  'python scripts/list_envs.py'
```

查看 replay 样例脚本参数：

```bash
docker compose --env-file docker/.env.base -f docker/docker-compose.yaml run --rm tabero -lc \
  'python scripts/tools/replay_demos.py --help'
```

## 测试结果

| 测试项 | 结果 | 说明 |
| --- | --- | --- |
| Docker Compose config | PASS | `docker compose ... config` 可正常解析。 |
| Docker image build | PASS | `tabero-isaaclab:latest` 构建成功。 |
| GPU 可见性 | PASS | 容器内 `nvidia-smi -L` 可见 4 张 NVIDIA RTX PRO 6000 Blackwell GPU。 |
| Python wrapper | PASS | 容器内 `python -V` 输出 `Python 3.11.13`，路径为 `/usr/local/bin/python`。 |
| OpenPI client tests | PASS | `21 passed in 0.23s`。 |
| Replay CLI help | PASS | `python scripts/tools/replay_demos.py --help` 可正常输出参数。 |
| Tabero env registry | PASS | `python scripts/list_envs.py` 可 headless 启动 Isaac Lab，并列出 23 个 `tac_manip` 环境。 |
| LIBERO 数据下载 | PASS | `NathanWu7/Isaaclab_Libero` 完整 snapshot 已下载到 `local_datasets/Isaaclab_Libero`，校验 13103 个文件、约 1.666 GiB，无缺失或大小不一致文件。 |
| 触觉资源下载 | PASS | `china-sae-robotics/Tactile_Manipulation_Dataset` 已下载到 `local_datasets/Tactile_Manipulation_Dataset`，`assets/data` 下 40 个资源文件可见。 |
| 容器内数据可见性 | PASS | 容器内 `find -L` 可见 `assembled_hdf5=40`、`replayed_demos=40`、`video_datasets=4018`、`USD=121`、触觉资源 `40`。 |
| Replay recollection smoke | PASS | `replay_demos_with_camera.py --dump_data` 从 `assembled_hdf5` 回放 `libero_goal task0 demo0`，执行 138 steps，并导出 `local_datasets/replay_smoke/replayed_demos/libero_goal_task0_open_the_middle_drawer_of_the_cabinet_replayed_demo.hdf5`。 |
| 下载版 replayed demo 回放 | PASS/WARN | `replay_demos.py` 可从下载版 `replayed_demos` 读取 `libero_goal task0 demo0` 并完整跑完 138 steps，命令退出码为 0；该 demo 在 `Isaac-Libero-Franka-IK-v0` 下未触发 success 条件，写入 `failure.jsonl`。这是任务成功率结果，不是环境或数据路径阻塞。 |

`scripts/list_envs.py` 启动 Isaac Lab 时出现以下非致命 warning：

- `failed to open the default display`：headless 容器内常见。
- `CPU performance profile is set to powersave`：主机性能配置提示。
- `IOMMU is enabled` 与 `peer access is already enabled`：GPU peer access 检测提示；命令最终退出码为 0。

## 当前阻塞或未覆盖项

完整数据已下载，单条 replay smoke 已跑通。仍未覆盖或需要外部服务的项目：

- OpenPI 模型服务：`benchmarks/openpi/openpi_inference_client.py` 需要对应 policy server 才能做端到端推理，本次只验证了仓库侧 OpenPI client 单元测试。
- 任务成功率：下载版 `libero_goal task0 demo0` 在 `Isaac-Libero-Franka-IK-v0` 下完整执行但未触发 success；后续论文级复现应按 suite/task 批量统计，并区分环境可运行性与 policy/control 成功率。
- `hf-mirror.com` 在本机环境下对 Hugging Face metadata HEAD 请求不稳定，本次通过 `unset HF_ENDPOINT` 使用官方 endpoint 下载成功；如果网络中断，重复执行 `hf download` 可复用缓存继续补齐。

后续可以直接进入长期运行容器继续做转换、训练、OpenPI policy server 联调和 Tabero 改进实验。
