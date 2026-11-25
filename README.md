# ImmuNiche Lab

免疫细胞状态、空间生态位分析与模型结果解读工作台。

## 功能

- 单细胞 PCA、细胞类型、基因表达和代谢相关表达程序。
- 两张 MERSCOPE 样本的空间图、细胞类型映射和多尺度邻域生态位。
- 生态位组成、细胞详情、映射支持度与归属概率。
- 智能体查询实际结果，解释生态位特征、比较样本并展示查询依据。
- 下载输入清单、逐细胞结果、完整分析结果和图像。

## 运行 Python 分析与网页

```bash
python -m pip install -r requirements.txt
python code/webapp/server.py --port 8765
```

打开 `http://127.0.0.1:8765`。Windows 可双击 `启动网页.cmd`。

提供了可直接运行的真实开发子集及已计算基线，启动后即可浏览。点击“重新运行示例基线”可重新计算。

智能体从服务端环境变量 `DEEPSEEK_API_KEY` 读取凭据。网页展示分析对话，凭据不进入前端或版本库。问题、最近对话与工具查询汇总会发送至模型服务。

## 输入数据

- [GSE132465](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE132465)：2位患者的肿瘤单细胞子集，2,709个细胞、33,694个基因。
- [Vizgen 公开数据](https://vizgen.com/data-release-program/)：HumanColonCancerPatient1、Patient2 的局部连续区域，分别4,000和3,998个细胞，500个生物基因。

三份数据共有497个基因；单细胞与空间来自同癌种的独立队列。输入矩阵、基因顺序和细胞元信息位于 `data/local_example`。数据来源与输入清单随数据保存，第三方数据遵循原发布方使用条款。

## 方法

共有基因归一化、PCA和kNN用于细胞类型映射，并按参考患者留出验证。空间邻域特征包含细胞类型组成与可测表达程序，采用12或24近邻、3至6类GMM。样本1拟合的GMM应用于样本2。

当前发布版本展示映射和GMM基线。精细巨噬细胞连续状态与双分支GNN为后续模型开发内容。髓系标签、映射支持度、生态位概率和表达评分分别保留。

## 线上部署

线上版运行 Cloudflare Worker，提供真实示例结果、完整面板内基因查询和智能体解读。重新建模在 Python 环境执行，更新结果后构建部署。

```bash
python scripts/build_worker.py
node --test worker/test.mjs
```

构建产物为 `dist/server/index.js`。托管平台中配置服务端密钥 `DEEPSEEK_API_KEY`，可选配置 `DEEPSEEK_MODEL`。`.openai/hosting.json` 保存 Sites 项目标识。

## 验证

```bash
python -m unittest discover -s code/webapp -p test_agent.py
node --test worker/test.mjs
```

测试覆盖实际表达读取、基因缺测、生态位及邻居计数、工具调用流程和凭据隔离。线上智能体和本地智能体均只提供结果查询工具。
