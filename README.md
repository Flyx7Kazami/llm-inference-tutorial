# LLM 推理优化学习路线

> 面向懂算法、想补工程推理优化知识的同学。从「为什么慢」出发，逐层拆解优化手段。

**在线阅读：<https://flyx7kazami.github.io/llm-inference-tutorial/>**

## 你会学到什么

- LLM 推理的两个阶段（Prefill / Decode）及其截然不同的性能特征
- 为什么推理是 **memory-bound** 而非 compute-bound
- KV Cache 的原理、痛点与优化（PagedAttention 等）
- 量化的数学原理与工程实践（GPTQ / AWQ / FP8）
- 并行策略：Tensor / Pipeline / Data / Sequence / Context / Expert Parallelism
- 进阶技术：Speculative Decoding / FlashAttention / Kernel Fusion
- 主流推理框架对比（vLLM / TGI / TensorRT-LLM / SGLang）
- **推理集群与基础设施：Autoscaling、负载均衡、GPU 资源管理、成本优化**

## 学习路线

| 顺序 | 章节 | 核心问题 |
|------|------|----------|
| 1 | [推理基础](https://flyx7kazami.github.io/llm-inference-tutorial/chapters/01_inference_fundamentals.html) | 推理到底慢在哪？ |
| 2 | [KV Cache 与内存优化](https://flyx7kazami.github.io/llm-inference-tutorial/chapters/02_kv_cache_and_memory.html) | 显存都去哪了？ |
| 3 | [量化](https://flyx7kazami.github.io/llm-inference-tutorial/chapters/03_quantization.html) | 精度换速度，到底怎么换？ |
| 4 | [并行与服务架构](https://flyx7kazami.github.io/llm-inference-tutorial/chapters/04_parallelism_and_serving.html) | 大模型怎么切、怎么服务？ |
| 5 | [进阶优化技术](https://flyx7kazami.github.io/llm-inference-tutorial/chapters/05_advanced_techniques.html) | 还有哪些黑科技？ |
| 6 | [推理框架生态](https://flyx7kazami.github.io/llm-inference-tutorial/chapters/06_framework_ecosystem.html) | 生产环境用什么？ |
| 7 | [**推理集群与基础设施**](https://flyx7kazami.github.io/llm-inference-tutorial/chapters/07_cluster_and_infra.html) | **怎么弹性伸缩、省着花钱？** |

## 章节关系图

```
单卡优化层                    集群运维层
┌──────────────────┐         ┌──────────────────┐
│ 1. 推理基础       │         │ 7. 集群与基础设施  │
│   (为什么慢)      │         │   (怎么跑在云上)   │
├──────────────────┤         ├──────────────────┤
│ 2. KV Cache      │         │ · Autoscaling     │
│ 3. 量化          │────────►│ · 负载均衡 & 路由  │
│ 4. 并行          │  单卡优化 │ · GPU 资源管理     │
│ 5. 进阶技术      │  决定了  │ · CPU/GPU 混合    │
│ 6. 框架选型      │  集群规模 │ · 成本优化        │
└──────────────────┘         └──────────────────┘
```

## 建议学习方式

1. 按顺序读，每章都有「算法同学容易混淆的直觉」提示
2. 每章末尾有思考题，建议自己想一下再看答案
3. 涉及代码的地方会给出最小可运行示例（PyTorch）
4. 第 7 章涉及 K8s / 云服务，建议结合实际部署经验理解

## 仓库结构

- `site/`：构建好的静态站点，GitHub Pages 直接发布此目录
- `build_site.py`：markdown → 静态站点的构建脚本（章节 markdown 源文件未包含在本仓库）
- `.github/workflows/pages.yml`：push 到 `main` 后自动部署到 GitHub Pages
