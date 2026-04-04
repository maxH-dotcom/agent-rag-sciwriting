# 科研助手 MVP - 零基础使用指南

> 上传数据 + 输入研究问题 = 自动生成可运行的统计分析代码

---

## 这个工具能做什么？

假设你有这样一份数据（浙江省各城市 2000-2023 年）：

| 年份 | 地区 | 农业产值(亿元) | 碳排放总量 | 农药使用量 |
|------|------|----------------|------------|------------|
| 2000 | 杭州 | 50.2 | 120.5 | 2.3 |
| 2001 | 杭州 | 52.1 | 125.8 | 2.4 |
| ... | ... | ... | ... | ... |

你想研究"农业产值对碳排放有什么影响"。

**传统方式**：花几小时查文献、选模型、写代码

**用这个工具**：输入一句话，自动生成完整代码，直接在 Google Colab 运行

---

## 目录

1. [快速开始](#一快速开始-只需30分钟)
2. [环境安装](#二环境安装-首次需要)
3. [运行程序](#三运行程序)
4. [使用生成的代码](#四使用生成的代码)
5. [常见问题](#五常见问题)

---

## 一、快速开始（只需30分钟）

### 第一步：打开终端

**Mac 用户**：
- 按 `Command + 空格`，搜索"终端"，回车

**Windows 用户**：
- 按 `Win + R`，输入 `cmd`，回车

### 第二步：进入项目文件夹

在终端中输入（复制粘贴后回车）：

```bash
cd /Volumes/hmq/智能科研工作助手/scw\ agent\ mvp
```

### 第三步：激活环境

```bash
source venv/bin/activate
```

### 第四步：设置 API Key（免费）

这个工具需要调用 AI 模型来理解你的研究问题。使用 Groq 免费 API：

1. 打开 https://console.groq.com/ 注册账号（用 Google 账号即可）
2. 登录后点击 "API Keys" → "Create Key"
3. 复制获得的 Key（以 `gsk_` 开头）

在终端中设置（把 `gsk_xxx` 换成你的真实 Key）：

```bash
export LLM_PROVIDER=groq
export GROQ_API_KEY=gsk_你的真实key
```

### 第五步：运行

```bash
python scripts/main.py
```

### 第六步：输入研究问题

程序运行后，会提示你输入研究问题。例如：

```
请输入研究问题: 我想分析农业产值对碳排放的影响
```

按回车，程序会自动完成所有步骤，最后询问是否生成代码文件，输入 `y` 回车。

### 第七步：在浏览器中打开代码

看到"完成"提示后，在文件夹 `notebooks/output/` 下会生成一个 `.ipynb` 文件。

---

## 二、环境安装（首次需要）

如果上面的快速开始能正常运行，跳过此部分。

如果报错"找不到命令"，需要按以下步骤安装。

### 2.1 安装 Python

#### Mac 用户

1. 打开 https://brew.sh/
2. 复制安装命令到终端，回车
3. 等待安装完成（可能需要几分钟）

然后在终端运行：
```bash
brew install python@3.11
```

#### Windows 用户

1. 打开 https://www.python.org/downloads/
2. 下载 Python 3.11
3. 运行安装程序，**务必勾选"Add Python to PATH"**

### 2.2 创建虚拟环境

在终端中运行：

```bash
cd /Volumes/hmq/智能科研工作助手/scw\ agent\ mvp
python3.11 -m venv venv
```

### 2.3 安装依赖

```bash
./venv/bin/pip install -r requirements.txt
```

如果下载太慢，试试：
```bash
./venv/bin/pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

### 2.4 验证安装

```bash
./venv/bin/python -c "import pandas; print('安装成功')"
```

看到"安装成功"即可。

---

## 三、运行程序

### 3.1 每次使用的完整流程

```bash
# 1. 进入文件夹
cd /Volumes/hmq/智能科研工作助手/scw\ agent\ mvp

# 2. 激活环境（必须）
source venv/bin/activate

# 3. 设置 API
export LLM_PROVIDER=groq
export GROQ_API_KEY=gsk_你的key

# 4. 运行
python scripts/main.py
```

### 3.2 输入研究问题的技巧

**好的例子**：
- `我想分析农业产值对碳排放的影响`
- `农民收入和粮食产量的关系`
- `化肥使用量对碳排放强度的影响，同时控制地区和年份`

**研究问题格式**：
- 说明你想分析什么变量对什么变量的影响
- 用"对"或"和"连接变量
- 可以加"控制xxx"来说明要控制的变量

### 3.3 程序输出什么？

程序会依次显示：

1. **数据信息**：加载的数据长什么样（行数、列数）
2. **问题解析**：AI 理解后的因变量(Y)、自变量(X)、控制变量
3. **数据结构**：判断是面板数据还是其他类型
4. **模型推荐**：推荐适合的统计模型及文献依据
5. **文献检索**：找到的相关文献
6. **代码生成**：生成 .ipynb 文件

---

## 四、使用生成的代码

### 4.1 上传到 Google Colab

1. 打开浏览器，访问 https://colab.research.google.com
2. 点击"上传"标签
3. 选择文件夹 `notebooks/output/` 下的 `.ipynb` 文件

### 4.2 在 Colab 中运行

1. 点击代码块左侧的播放按钮（绿色圆圈），或按 `Shift + Enter`
2. 依次运行所有代码块
3. 查看分析结果

### 4.3 可能需要修改的地方

如果数据文件不在代码同一目录，需要修改数据路径：

在第一个代码块中，找到：
```python
df = pd.read_csv('zhejiang_carbon.csv')
```

改成你的数据文件路径，例如：
```python
df = pd.read_csv('/content/my_data.csv')
```

### 4.4 下载为普通 Python 文件

如果不想用 Colab，可以在 Colab 中点击"文件" → "下载" → "下载 .py"

---

## 五、常见问题

### Q1: 报错"command not found"

**问题**：`cd: command not found`

**解决**：输入有误，路径中的空格需要加反斜杠，或用引号包裹：
```bash
cd "/Volumes/hmq/智能科研工作助手/scw agent mvp"
```

---

### Q2: 报错"No module named"

**问题**：`ModuleNotFoundError: No module named 'xxx'`

**解决**：依赖没装好，重新运行：
```bash
source venv/bin/activate
pip install -r requirements.txt
```

---

### Q3: 报错"LLM call failed"

**问题**：`WARNING: LLM call failed`

**原因**：API Key 无效或网络问题

**解决**：
1. 确认 API Key 正确且完整（以 `gsk_` 开头）
2. 检查网络连接
3. 程序会自动使用备用方案，不影响使用

---

### Q4: 生成的代码运行报错

**问题**：在 Colab 中运行代码时报错

**解决**：
1. 点击"代码块" → "运行前重置" → "运行所有"
2. 检查数据文件路径是否正确
3. 检查变量名是否和数据列名一致

---

### Q5: 中文显示乱码

**解决**：在 Colab 第一个代码块添加：
```python
# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False
```

---

### Q6: 如何分析自己的数据？

**步骤**：
1. 把你的数据（CSV 或 Excel）放到 `data/` 文件夹
2. 修改 `scripts/main.py` 中的数据路径（或者在运行时按提示操作）
3. 运行程序

**数据格式要求**：
- 必须有地区/城市列（如"地区"、"城市"）
- 必须有年份列（如"年份"、"年"）
- 其他列是你要分析的变量

---

### Q7: 支持哪些统计模型？

| 模型 | 适用场景 | 例子 |
|------|----------|------|
| 固定效应模型 (FE) | 面板数据，控制地区差异 | 11个城市20年的碳排放数据 |
| 随机效应模型 (RE) | 面板数据，个体效应随机 | 同上 |
| 双重差分 (DID) | 政策评估，有处理组和对照组 | 环保政策效果评估 |
| OLS 回归 | 截面数据，一次性调查 | 某年各省数据 |
| ARIMA | 时间序列预测 | 预测未来碳排放 |

---

### Q8: 如何获取 API Key？

**推荐 Groq（免费，高速）**：
1. 打开 https://console.groq.com/
2. 用 Google 账号注册
3. 点击"API Keys" → "Create"
4. 复制 Key

**备选 OpenAI**：
1. 打开 https://platform.openai.com/
2. 注册并充值
3. 创建 API Key

---

## 命令速查表

```bash
# 每次使用都要执行的（按顺序）
cd /Volumes/hmq/智能科研工作助手/scw\ agent\ mvp
source venv/bin/activate
export LLM_PROVIDER=groq
export GROQ_API_KEY=你的key
python scripts/main.py
```

---

## 文件夹结构说明

```
scw agent mvp/
├── README.md              # 本文档
├── requirements.txt       # 依赖列表
├── venv/                  # Python 环境（自动生成）
├── data/
│   └── zhejiang_carbon.csv   # 示例数据
├── scripts/
│   ├── main.py            # 主程序
│   ├── model_recommender.py  # 模型推荐
│   ├── parse_question.py     # 问题解析
│   ├── literature_retriever.py  # 文献检索
│   └── notebook_generator.py   # 代码生成
├── notebooks/
│   └── output/            # 生成的代码在这里
└── tests/
    └── test_pipeline.py   # 测试文件
```

---

## 技术支持

遇到问题请提供：
1. 完整的错误信息（截图或复制文字）
2. 你输入的研究问题
3. 数据列名（可以不透露数据内容）

---

*最后更新：2026-04-04*
