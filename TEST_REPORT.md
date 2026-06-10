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

`scripts/list_envs.py` 启动 Isaac Lab 时出现以下非致命 warning：

- `failed to open the default display`：headless 容器内常见。
- `CPU performance profile is set to powersave`：主机性能配置提示。
- `IOMMU is enabled` 与 `peer access is already enabled`：GPU peer access 检测提示；命令最终退出码为 0。

## 当前阻塞或未覆盖项

完整 replay / OpenPI 推理评测尚未执行，因为它需要外部数据和服务：

- LIBERO 数据：需要从 `NathanWu7/Isaaclab_Libero` 下载，并软链接到 `benchmarks/datasets/libero`。
- 触觉标定资源：使用 tactile 环境时需要从 `china-sae-robotics/Tactile_Manipulation_Dataset` 下载，并软链接到 `source/tac_manip/tac_manip/assets/data`。
- OpenPI 模型服务：`benchmarks/openpi/openpi_inference_client.py` 需要对应 policy server 才能做端到端推理。

下载数据后，可继续运行 README 中的 replay / conversion / inference 命令进行论文实验级复现。
