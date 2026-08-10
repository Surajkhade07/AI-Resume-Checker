import re
from typing import Dict, List, Set
from rapidfuzz import fuzz

SKILL_ALIASES: Dict[str, str] = {
    'reactjs': 'react',
    'react.js': 'react',
    'angularjs': 'angular',
    'vuejs': 'vue',
    'vue.js': 'vue',
    'nextjs': 'next.js',
    'nodejs': 'node.js',
    'node': 'node.js',
    'expressjs': 'express',
    'express.js': 'express',
    'springboot': 'spring boot',
    'golang': 'go',
    'ml': 'machine learning',
    'ai': 'artificial intelligence',
    'nlp': 'natural language processing',
    'cv': 'computer vision',
    'k8s': 'kubernetes',
    'sklearn': 'scikit-learn',
    'scikit learn': 'scikit-learn',
    'postgres': 'postgresql',
    'dotnet': '.net',
    'tailwindcss': 'tailwind',
    'amazon web services': 'aws',
    'google cloud': 'gcp',
    'google cloud platform': 'gcp',
    'pyspark': 'spark',
    'huggingface': 'hugging face',
    'deep learning (dl)': 'deep learning',
    'dl': 'deep learning',
    'ann': 'artificial neural networks',
    'cnn': 'convolutional neural networks',
    'rnn': 'recurrent neural networks',
    'rag': 'retrieval-augmented generation',
    'gans': 'generative adversarial networks',
    'gan': 'generative adversarial networks',
    'agentic ai': 'ai agents',
    'power bi': 'powerbi',
    'vs code': 'visual studio code',
    'vscode': 'visual studio code',
    'jupyter notebook': 'jupyter',
    'jupyter notebooks': 'jupyter',
    'tf': 'tensorflow',
    'ts': 'typescript',
    'js': 'javascript',
}

# Related contextual terms and synonyms that validate a skill in project/experience descriptions
SKILL_SYNONYMS: Dict[str, List[str]] = {
    'natural language processing': ['nlp', 'text processing', 'spacy', 'nltk', 'transformers', 'bert', 'llm', 'tokenization', 'sentiment analysis', 'named entity', 'ner'],
    'deep learning': ['dl', 'neural network', 'neural networks', 'pytorch', 'tensorflow', 'keras', 'cnn', 'rnn', 'ann', 'backpropagation', 'epoch', 'cuda', 'gpu'],
    'data visualization': ['visualization', 'visualizations', 'matplotlib', 'seaborn', 'power bi', 'powerbi', 'tableau', 'plotly', 'dashboard', 'dashboards', 'charts', 'plots'],
    'sql': ['mysql', 'postgresql', 'sqlite', 'oracle', 'sql queries', 'database queries', 'rdbms', 'pl/sql', 'tsql'],
    'git': ['github', 'gitlab', 'bitbucket', 'version control', 'git commit', 'git branch', 'git repo', 'repository'],
    'model evaluation': ['evaluation', 'accuracy', 'precision', 'recall', 'f1', 'f1-score', 'f1 score', 'roc-auc', 'auc', 'confusion matrix', 'cross-validation', 'metrics', 'loss'],
    'predictive analytics': ['predictive modeling', 'prediction', 'predictive model', 'regression', 'classification', 'forecasting', 'time series'],
    'pandas': ['dataframe', 'dataframes', 'data manipulation', 'data preprocessing', 'pd.read', 'series'],
    'numpy': ['ndarray', 'array manipulation', 'numerical computing', 'matrices', 'matrix operations', 'np.array'],
    'pytorch': ['torch', 'torchvision', 'nn.module', 'tensor', 'tensors', 'dataloader'],
    'tensorflow': ['tf', 'keras', 'tensor', 'tensors', 'tf.keras'],
    'keras': ['tensorflow', 'sequential', 'dense layer', 'conv2d', 'callbacks'],
    'streamlit': ['streamlit app', 'web app', 'st.write', 'st.sidebar', 'interactive dashboard'],
    'ann': ['artificial neural network', 'artificial neural networks', 'neural network', 'mlp', 'multilayer perceptron', 'dense layers'],
    'cnn': ['convolutional neural network', 'convolutional neural networks', 'convnet', 'image classification', 'object detection', 'computer vision', 'yolo', 'opencv'],
    'rnn': ['recurrent neural network', 'recurrent neural networks', 'lstm', 'gru', 'sequence-to-sequence', 'seq2seq', 'time series'],
    'rag': ['retrieval-augmented generation', 'retrieval augmented generation', 'vector database', 'vectordb', 'chromadb', 'faiss', 'pinecone', 'embeddings', 'chunking', 'retrieval'],
    'gans': ['generative adversarial networks', 'generative adversarial network', 'gan', 'generator', 'discriminator', 'synthetic data'],
    'agentic ai': ['ai agents', 'autonomous agents', 'agent', 'agents', 'langchain', 'langgraph', 'crewai', 'autogen', 'tool calling', 'function calling', 'reasoning'],
    'jupyter notebook': ['jupyter', 'ipynb', 'google colab', 'colab', 'notebook'],
    'vs code': ['visual studio code', 'vscode', 'ide', 'code editor'],
    'power bi': ['powerbi', 'dax', 'power query', 'bi dashboard', 'bi reports'],
    'machine learning': ['ml', 'supervised learning', 'unsupervised learning', 'scikit-learn', 'sklearn', 'random forest', 'xgboost', 'gradient boosting', 'svm'],
    'java': ['spring', 'spring boot', 'jvm', 'j2ee', 'hibernate'],
    'python': ['py', 'fastapi', 'flask', 'django', 'pytest', 'pip', 'python3'],
}


def get_skill_variants(skill: str) -> List[str]:
    """Decompose skill into canonical names, acronyms in parentheses, and clean forms."""
    variants: Set[str] = set()
    cleaned = skill.strip()
    if not cleaned:
        return []

    variants.add(cleaned.lower())

    # 1. Check for parentheses: "Natural Language Processing (NLP)" -> ["natural language processing", "nlp"]
    m = re.match(r'^(.*?)\s*\((.*?)\)$', cleaned)
    if m:
        main_part = m.group(1).strip().lower()
        acronym_part = m.group(2).strip().lower()
        if main_part:
            variants.add(main_part)
        if acronym_part:
            variants.add(acronym_part)

    # 2. Check for slashes or commas: "CI/CD" or "Seaborn / Matplotlib"
    if '/' in cleaned:
        for part in cleaned.split('/'):
            p = part.strip().lower()
            if p:
                variants.add(p)

    # 3. Add canonical alias if exists
    canon = SKILL_ALIASES.get(cleaned.lower())
    if canon:
        variants.add(canon)

    for v in list(variants):
        c = SKILL_ALIASES.get(v)
        if c:
            variants.add(c)

    return list(variants)


def normalize_skill(skill: str) -> str:
    cleaned = skill.strip().lower()
    # Strip trailing (acronym) for canonical normalization
    m = re.match(r'^(.*?)\s*\(.*?\)$', cleaned)
    if m:
        cleaned = m.group(1).strip()
    return SKILL_ALIASES.get(cleaned, cleaned)


def fuzzy_match_keywords(
    resume_keywords: List[str],
    jd_keywords: List[str],
    threshold: int = 80,
) -> Dict[str, List[str]]:
    resume_normalized = {normalize_skill(kw): kw for kw in resume_keywords}
    # Also add decomposed variants
    for kw in resume_keywords:
        for v in get_skill_variants(kw):
            resume_normalized[v] = kw

    jd_normalized = {normalize_skill(kw): kw for kw in jd_keywords}

    matched_jd_originals = []
    missing_jd_originals = []

    for jd_canon, jd_original in jd_normalized.items():
        # 1. Exact canonical match
        if jd_canon in resume_normalized:
            matched_jd_originals.append(jd_original)
            continue

        # 2. Substring token match
        if any(jd_canon == rk or (len(jd_canon) > 3 and jd_canon in rk) for rk in resume_normalized):
            matched_jd_originals.append(jd_original)
            continue

        # 3. Fuzzy match against all resume canonical names
        best_score = 0
        for resume_canon in resume_normalized:
            score = fuzz.token_sort_ratio(jd_canon, resume_canon)
            best_score = max(best_score, score)

        if best_score >= threshold:
            matched_jd_originals.append(jd_original)
        else:
            missing_jd_originals.append(jd_original)

    return {
        'matched': sorted(list(set(matched_jd_originals))),
        'missing': list(set(missing_jd_originals)),
    }