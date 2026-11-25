# ImmuNiche Lab

在项目根目录双击“启动网页.cmd”，或运行：

```powershell
python -X utf8 code/webapp/server.py --port 8765
```

打开 http://127.0.0.1:8765 。首次启动会计算示例基线，之后直接读取保存的结果。

## 已实现

- 真实示例数据概览、原作者细胞类型与共有基因PCA。
- 脯氨酸、活性硫／氧化还原及免疫功能相关表达评分；覆盖不足的程序显示实际覆盖情况。
- 按患者留出的细胞类型映射验证，以及两张Vizgen样本的细胞类型映射。
- 12／24近邻、3至6类GMM生态位基线；用样本1拟合，应用于样本2。
- 空间缩放、平移、细胞详情、生态位组成筛选及实际基因表达查询。
- 下载输入清单、细胞结果、完整分析JSON和图像；网页按钮重新计算基线。

## 智能体

服务启动时通过 `DEEPSEEK_API_KEY` 环境变量读取凭据，模型从账户实时获取。网页仅展示“智能体”及分析对话，凭据在服务端配置。

智能体支持数据概览、基因覆盖及表达统计、程序评分和生态位组成查询，回答下方显示工具查询记录。问题、最近对话及查询汇总发送至 DeepSeek 官方 API；原始矩阵和逐细胞标识保留本机。

接口参考：[DeepSeek 工具调用](https://api-docs.deepseek.com/guides/tool_calls/)、[模型列表](https://api-docs.deepseek.com/api/list-models/)。

离线验证：在 code/webapp 目录执行 `python -m unittest test_agent.py`。测试使用本地数据和模拟接口；实际账户连通性在填写 Key 后验证。

## 分析范围

当前展示细胞类型映射和邻域生态位基线。细胞类型中的“Myeloids”表示髓系细胞；精细巨噬细胞连续状态与双分支GNN为下一开发阶段。

示例单细胞按细胞类型抽样，空间为局部裁剪。网页中的分类支持度和GMM归属概率分别展示。样本的程序表达评分在各自测得基因内计算；代谢物、通量、过硫化修饰另由实验测量。

## 文件

- 输入：data/local_example/manifest.json。
- 分析：code/webapp/analysis.py。
- 服务：code/webapp/server.py，绑定127.0.0.1。
- 网页：code/webapp/static。
- 结果：runs/web_demo/analysis.json及各数据集annotations.tsv。

运行需要Python、numpy、pandas、scipy、scikit-learn；本机已具备这些依赖。网页采用原生HTML/CSS/JavaScript，无需npm安装或外部CDN。
