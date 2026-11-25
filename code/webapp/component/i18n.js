/* UI language only; scientific inputs and exported source metadata stay intact. */
(() => {
  const terms={
    '分析':'Analysis','研究':'Research','本地运行':'Local session','在线运行':'Online session',
    '数据概览':'Overview','细胞状态与代谢':'Cell states & metabolism','空间与生态位':'Spatial niches','分析流程与记录':'Methods & records','智能体':'Research assistant',
    '从细胞状态，看到组织环境':'From cell states to tissue environments','先认识输入数据，再追踪代谢程序与局部细胞组合。':'Explore the inputs, metabolic programs and local cell communities.',
    '下载输入清单':'Download manifest','真实数据 · 开发示例':'Real data · Development demo','GSE132465 × Vizgen 肠癌':'GSE132465 × Vizgen colorectal cancer',
    '输入细胞':'Input cells','单细胞与两份空间裁剪区域':'Single-cell reference and two spatial crops','空间样本':'Spatial sample','每份约4,000个细胞':'About 4,000 cells per sample',
    '共有基因':'Shared genes','用于跨平台细胞类型映射':'Used for cross-platform cell-type mapping','单细胞患者':'Reference patients','按患者留出验证':'Leave-one-patient-out validation',
    '输入数据':'Input data','独立保存计数、基因和细胞信息':'Counts, genes and observation metadata','表达与原作者注释':'Expression and published annotations','细胞表达与空间坐标':'Expression and spatial coordinates','查看':'Open',
    '当前分析进度':'Analysis progress','已完成的基线与下一步模型':'Current baselines and model development','输入校验':'Input checks','计数、细胞ID和空间坐标对齐':'Counts, cell IDs and coordinates aligned',
    '细胞类型映射':'Cell-type mapping','空间邻域与生态位基线':'Spatial neighborhoods & niche baseline','双分支 GNN':'Dual-branch GNN','自身状态、环境表示与独立患者比较':'Cell-intrinsic states, environment and patient-level validation',
    '下一步：接入自身状态与空间环境双分支 GNN，对照现有基线评估新患者表现。':'Next: add a dual-branch GNN and compare performance on independent patients.',
    '查看空间结果':'Explore spatial results','看什么，得到什么':'Explore the analysis','细胞自身与周围环境分别查看，组合分析。':'Inspect cell-intrinsic states and neighboring environments together.',
    '细胞自身状态':'Cell-intrinsic states','查看细胞类型、代谢相关表达和免疫功能程序。':'Explore cell types, metabolic expression and immune programs.',
    '周围空间环境':'Local environments','查看相邻细胞组成，以及不同尺度的局部组合。':'Explore neighboring cell composition across scales.',
    '目标生态位':'Candidate niches','比较样本中的生态位分布，形成后续机制分析对象。':'Compare niche distributions and identify candidates for mechanistic analysis.',
    '本地示例项目':'Example project','肠癌 · 单细胞 + MERSCOPE':'CRC · Single-cell + MERSCOPE','所有图表来自本机真实数据，结果保存在项目 runs 目录。':'Charts use real local inputs; results are saved in the project runs directory.',
    '本地分析 · 按需 AI 查询':'Local analysis · On-demand assistant','输入 / 基线分析 / 交互查看':'Inputs / Baselines / Exploration','本机真实数据 · 示例基线 · 保留原始输入':'Real inputs · Example baselines · Source data retained',
    'GSE132465 · 2位患者的肿瘤细胞子集':'GSE132465 · Tumor cells from two patients','下载细胞结果':'Download cell results','着色方式':'Color by','原作者细胞类型':'Published cell types','患者':'Patient','表达基因':'Gene','显示':'Show',
    '脯氨酸相关表达':'Proline-related expression','活性硫／氧化还原相关表达':'Reactive sulfur / redox expression','基因原始计数':'Raw gene counts','细胞表达分布':'Expression embedding',
    '共有基因 PCA · 点击细胞查看详情':'Shared-gene PCA · Select a cell for details','保存 PNG':'Save PNG','细胞详情':'Cell details','选择图中的一个细胞':'Select a cell in the plot','点击散点，查看细胞类型、患者和表达程序。':'Select a point to inspect its type, patient and expression programs.',
    '细胞组成':'Cell composition','细胞类型与表达程序':'Cell types & expression programs','颜色按每列缩放；数值为该类细胞的平均表达评分':'Colors are scaled per column; values are mean expression scores for each cell type.',
    '真实计数计算':'Computed from real counts','细胞类型':'Cell type','抗原呈递':'Antigen presentation','炎症相关表达':'Inflammatory expression','免疫调节相关表达':'Immune regulation','基质重塑相关表达':'Matrix remodeling','细胞毒相关表达':'Cytotoxic expression',
    '上皮细胞':'Epithelial cells','T细胞':'T cells','髓系细胞':'Myeloid cells','B细胞':'B cells','基质细胞':'Stromal cells','肥大细胞':'Mast cells','待确认':'Unassigned',
    '表达程序在本数据内计算，用于比较相关基因表达；代谢物、通量及蛋白修饰由实验测量。':'Programs compare gene expression within each dataset; metabolites, flux and protein modifications require experimental measurements.',
    '细胞位置、邻域组成与生态位归属。':'Cell locations, neighborhood composition and niche membership.','下载空间结果':'Download spatial results','生态位基线':'Niche baseline','映射细胞类型':'Mapped cell types','细胞类型映射支持度':'Mapping support','邻居数':'Neighbors','生态位数':'Niche count',
    '邻域基线 · GMM':'Neighborhood baseline · GMM','GNN：待接入':'GNN: planned','空间分布':'Spatial distribution','滚轮缩放 · 拖动平移 · 点击细胞':'Scroll to zoom · Drag to pan · Select a cell','复位':'Reset',
    '生态位细胞组成':'Niche cell composition','选择一个生态位，查看其中心细胞类型构成':'Select a niche to inspect its center-cell types.','全部':'All','点击空间图中的细胞，查看映射支持度与生态位归属概率。':'Select a spatial cell to inspect mapping support and niche membership.',
    '空间表达覆盖':'Spatial program coverage','按这份面板实际可测的基因显示程序':'Programs use genes measured by this panel.','本面板覆盖不足':'Insufficient panel coverage','可显示表达评分':'Expression score available','该程序基因未覆盖':'Program genes are not covered',
    '样本1用于拟合生态位基线，模型固定后应用于样本2；样本标签按来源保留，患者层面比较待补齐患者元信息。':'The baseline is fitted on sample 1 and applied to sample 2. Sample names follow the source; patient-level comparison requires patient metadata.',
    '输入、方法、验证结果和可复用输出。':'Inputs, methods, validation and reusable outputs.','重新运行示例基线':'Recompute baseline','基线已完成':'Baseline completed','流程状态':'Pipeline status','当前版本使用真实数据基线':'Current version uses real-data baselines.',
    '以另一位患者训练，预测留出患者细胞类型':'Train on the other patient and predict the held-out patient.','准确率':'Accuracy','方法与输入记录':'Methods & provenance','同一份输入可以重新计算与导出':'Recompute and export results from the same inputs.',
    '下载完整结果 JSON':'Download analysis JSON','查看输入清单':'View manifest','程序表达评分':'Program expression scores','归属结果':'Membership outputs','示例范围':'Demo scope',
    '验证来自按细胞类型抽样的开发子集。空间映射显示分类支持度；髓系细胞进一步划分巨噬细胞状态将在下一阶段接入。':'Validation uses a cell-type-stratified development subset. Spatial mapping reports classification support; finer macrophage states are planned.',
    '解读模型结果，解释生态位特征与样本差异。':'Interpret model results, niche features and sample differences.','待启用':'Not configured','已就绪':'Ready','分析对话':'Research conversation','结合当前空间模型解读，支持连续追问与查询依据。':'Interpret the selected spatial model with follow-up questions and query evidence.',
    '新对话':'New conversation','解读当前模型的生态位特征':'Interpret the selected niche model','比较两个空间样本的生态位细胞组成':'Compare niche composition across the two samples','结合 PYCR1 和 MPST 表达解读模型结果':'Interpret results using PYCR1 and MPST expression',
    '输入研究问题…':'Ask a research question…','发送问题':'Send question','你':'You','ImmuNiche 助手':'ImmuNiche assistant','服务配置完成后即可开始分析。':'The assistant will be available after server configuration.','正在查询与分析…':'Querying and interpreting results…',
    '正在读取真实分析结果':'Loading analysis results','连接本机示例数据与结果文件…':'Reading example inputs and computed outputs…','细胞ID':'Cell ID','映射类型':'Mapped type','映射支持度':'Mapping support','生态位':'Niche','归属概率':'Membership probability','空间坐标':'Coordinates',
    '计数':'Counts','阳性细胞':'Positive cells','所有细胞类型保留':'All cell types retained','模型已收敛':'Model converged','模型未收敛':'Model not converged','下载失败':'Download failed'
  };
  const methods={mapping:'Shared-gene normalization, standardization, PCA20 and distance-weighted kNN15.',scores:'Normalize each dataset to 10,000 counts, apply log1p and average covered genes; at least 3 genes and 50% coverage.',niche:'12/24-neighbor composition excluding the center cell, plus measured programs; fit scaling and GMM on sample 1 and apply to sample 2.',confidence:'Classification support and GMM membership probability are displayed separately and are not calibrated confidence.',sample_scope:'Development subsets: stratified single-cell sampling and local spatial crops. Spatial observations without patient metadata are shown by sample.'};
  let language='zh';try{language=localStorage.getItem('immuniche.language')||'zh';}catch{}
  const originals=new WeakMap();
  function translate(text){
    if(language!=='en')return text;
    const trim=text.trim();if(terms[trim])return text.replace(trim,terms[trim]);
    return text.replace(/计算于\s*/g,'Computed ').replace(/([\d,]+)\s*个细胞/g,'$1 cells').replace(/([\d,]+)\s*个基因/g,'$1 genes').replace(/([\d,]+)个共有基因/g,'$1 shared genes').replace(/按患者留出验证/g,'Patient-held-out validation').replace(/生态位\s*(\d+)/g,'Niche $1').replace(/样本\s*(\d+)/g,'Sample $1').replace(/留出患者\s*/g,'Held-out patient ').replace(/查询记录\s*·\s*(\d+)\s*次/g,'Query evidence · $1 calls').replace(/已完成\s*·\s*(\d+)\s*次工具查询/g,'Completed · $1 tool calls').replace(/待确认/g,'Unassigned').replace(/阳性细胞/g,'Positive cells').replace(/所有细胞类型保留/g,'All cell types retained').replace(/模型已收敛/g,'Model converged').replace(/模型未收敛/g,'Model not converged').replace(/未列于当前数据的基因清单/g,'is not measured in this dataset').replace(/未列于当前数据/g,'is not measured in this dataset').replace(/本面板不覆盖/g,'Panel does not cover').replace(/近邻/g,'neighbors');
  }
  function refresh(){
    observer.disconnect();
    if(typeof data!=='undefined'&&data){for(const [key,value] of Object.entries(data.methods))if(methods[key])terms[value]=methods[key];let index=0;for(const dataset of data.datasets){terms[dataset.name]=dataset.modality==='scrna'?'CRC single-cell · GSE132465':`Vizgen CRC · Sample ${++index}`;}}
    const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
    while(walker.nextNode()){
      const node=walker.currentNode;if(node.parentElement?.closest('script,style,pre,#uiLanguage,.agent-text'))continue;
      const record=originals.get(node);let original=node.nodeValue;
      if(record&&node.nodeValue===record.translated)original=record.original;
      const translated=translate(original);originals.set(node,{original,translated});if(node.nodeValue!==translated)node.nodeValue=translated;
    }
    for(const element of document.querySelectorAll('[placeholder],[title],[aria-label]'))for(const key of ['placeholder','title','aria-label']){
      if(!element.hasAttribute(key))continue;const storage=`data-i18n-${key}`;if(!element.hasAttribute(storage))element.setAttribute(storage,element.getAttribute(key));element.setAttribute(key,translate(element.getAttribute(storage)));
    }
    document.documentElement.lang=language==='en'?'en':'zh-CN';
    observer.observe(document.body,{subtree:true,childList:true,characterData:true});
  }
  const observer=new MutationObserver(refresh);
  window.NicheI18n={translate,get language(){return language;}};
  document.addEventListener('DOMContentLoaded',()=>{
    const select=document.getElementById('uiLanguage');if(select){select.value=language;select.onchange=()=>{language=select.value;try{localStorage.setItem('immuniche.language',language);}catch{}refresh();};}refresh();
  });
})();
