---
tags:
- sentence-transformers
- sentence-similarity
- feature-extraction
- generated_from_trainer
- dataset_size:350
- loss:CosineSimilarityLoss
base_model: sentence-transformers/all-mpnet-base-v2
widget:
- source_sentence: Lead Data Scientist bringing over 7 years of industry experience
    along with a verified Masters degree. Expert competencies cover Statistical hypothesis
    testing criteria, experimental design setups, and predictive pipelines. Proven
    success track record in extracting predictive features from massive volatile event
    tracking logs.
  sentences:
  - Seeking a skilled DevOps Systems Operations Architect to join our growing team.
    Key responsibilities include refactoring production scaling parameters to guarantee
    high system load availability specifications. Must be fully comfortable handling
    tools like CI/CD execution pipelines, custom automated deployment controls, and
    system telemetry metrics in a fast-paced environment.
  - Seeking a skilled Financial Quantitative Portfolio Analyst to join our growing
    team. Key responsibilities include authoring algorithmic pricing code architectures
    driven by statistical signal anomalies. Must be fully comfortable handling tools
    like Stochastic calculus integrations, Monte Carlo simulations, and historical
    backtesting data in a fast-paced environment.
  - Seeking a skilled Senior Backend Engineer to join our growing team. Key responsibilities
    include authoring secure distributed services capable of managing millions of
    requests concurrently. Must be fully comfortable handling tools like Node.js,
    Redis caching mechanisms, fault-tolerant RESTful API design, and multi-region
    AWS configs in a fast-paced environment.
- source_sentence: 'DevOps Specialist with 5 years working across active teams. Demonstrated
    technical execution and history background includes: Basic understanding of K8s,
    Theoretical knowledge of Cloud Infrastructure (AWS), Infrastructure as Code (IaC),
    Python. Seeking an engineering position to scale architectural patterns.'
  sentences:
  - Seeking a skilled Senior Data Scientist to join our growing team. Key responsibilities
    include architecting pipeline metrics to interpret user retention tracking patterns.
    Must be fully comfortable handling tools like Python scripting, R modeling, advanced
    SQL queries, and Apache Airflow pipelines in a fast-paced environment.
  - 'We are looking for a Infrastructure Platform Architect with a minimum of 4+ years
    of experience. The core technical stack requirements involve deep knowledge in:
    Docker, K8s, AWS Cloud Platform, Infrastructure as Code (IaC), Python. Must be
    highly capable of executing product deliverables in a fast paced workspace environment.'
  - Seeking a skilled Lead Quantitative Analytics Expert to join our growing team.
    Key responsibilities include driving critical product decisions via robust hypothesis
    experimental designs. Must be fully comfortable handling tools like A/B testing
    experimental frameworks, predictive regression modeling, and Tableau dashboards
    in a fast-paced environment.
- source_sentence: 'ML Engineer with 2 years working across active teams. Demonstrated
    technical execution and history background includes: Python3, Machine Learning,
    Theoretical knowledge of GenAI, Container Orchestration Engine, AWS Cloud Platform.
    Seeking an engineering position to scale architectural patterns.'
  sentences:
  - 'We are looking for a DevOps Cloud Engineer with a minimum of 4+ years of experience.
    The core technical stack requirements involve deep knowledge in: Docker, K8s,
    Cloud Infrastructure (AWS), Infrastructure as Code (IaC), Py3 Engine. Must be
    highly capable of executing product deliverables in a fast paced workspace environment.'
  - 'We are looking for a Computer Vision Scientist with a minimum of 3+ years of
    experience. The core technical stack requirements involve deep knowledge in: Py3
    Engine, Statistical Modeling, AI, Container Orchestration Engine, Docker, Cloud
    Infrastructure (AWS). Must be highly capable of executing product deliverables
    in a fast paced workspace environment.'
  - Seeking a skilled Deep Learning Systems Engineer to join our growing team. Key
    responsibilities include managing automated model retraining orchestration loops
    and tracking data drift. Must be fully comfortable handling tools like PyTorch
    optimization layers, distributed training loops, and CUDA kernels in a fast-paced
    environment.
- source_sentence: 'React Developer with 8 years working across active teams. Demonstrated
    technical execution and history background includes: JavaScript, React, Worked
    with PostgreSQL in minor capacity, TypeScript, OCI Containers. Seeking an engineering
    position to scale architectural patterns.'
  sentences:
  - 'We are looking for a Site Reliability Engineer with a minimum of 5+ years of
    experience. The core technical stack requirements involve deep knowledge in: Docker,
    K8s, Cloud Infrastructure (AWS), Terraform, Python. Must be highly capable of
    executing product deliverables in a fast paced workspace environment.'
  - 'We are looking for a Backend Engineer with a minimum of 5+ years of experience.
    The core technical stack requirements involve deep knowledge in: ECMAScript, ReactJS,
    Server-side Runtime, PostgreSQL, TS, Docker Containers. Must be highly capable
    of executing product deliverables in a fast paced workspace environment.'
  - 'We are looking for a Senior ML Engineer with a minimum of 5+ years of experience.
    The core technical stack requirements involve deep knowledge in: Python, ML, GenAI,
    K8s, OCI Containers, AWS Cloud Platform. Must be highly capable of executing product
    deliverables in a fast paced workspace environment.'
- source_sentence: 'Statistical Researcher with 2 years working across active teams.
    Demonstrated technical execution and history background includes: Theoretical
    knowledge of Python3, Academic projects utilizing PostgreSQL, Basic understanding
    of Statistical Modeling. Seeking an engineering position to scale architectural
    patterns.'
  sentences:
  - 'We are looking for a Lead Product Analyst with a minimum of 7+ years of experience.
    The core technical stack requirements involve deep knowledge in: Python, Postgres,
    Machine Learning, GenAI, AWS Cloud Platform. Must be highly capable of executing
    product deliverables in a fast paced workspace environment.'
  - Seeking a skilled Distributed Systems Software Architect to join our growing team.
    Key responsibilities include designing high-throughput message brokers and backend
    streaming infrastructures. Must be fully comfortable handling tools like Java,
    Spring Boot framework, microservices decoupling, and Apache Kafka streams in a
    fast-paced environment.
  - Seeking a skilled Senior Machine Learning Engineer to join our growing team. Key
    responsibilities include optimizing neural network tensor layers and inference
    latency pathways. Must be fully comfortable handling tools like LLM Fine-Tuning
    pipelines, Hugging Face Transformers, and Vector DB architectures in a fast-paced
    environment.
pipeline_tag: sentence-similarity
library_name: sentence-transformers
metrics:
- pearson_cosine
- spearman_cosine
model-index:
- name: SentenceTransformer based on sentence-transformers/all-mpnet-base-v2
  results:
  - task:
      type: semantic-similarity
      name: Semantic Similarity
    dataset:
      name: ats val
      type: ats-val
    metrics:
    - type: pearson_cosine
      value: 0.8695148627906333
      name: Pearson Cosine
    - type: spearman_cosine
      value: 0.8367820858386895
      name: Spearman Cosine
---

# SentenceTransformer based on sentence-transformers/all-mpnet-base-v2

This is a [sentence-transformers](https://www.SBERT.net) model finetuned from [sentence-transformers/all-mpnet-base-v2](https://huggingface.co/sentence-transformers/all-mpnet-base-v2). It maps sentences & paragraphs to a 768-dimensional dense vector space and can be used for retrieval.

## Model Details

### Model Description
- **Model Type:** Sentence Transformer
- **Base model:** [sentence-transformers/all-mpnet-base-v2](https://huggingface.co/sentence-transformers/all-mpnet-base-v2) <!-- at revision e8c3b32edf5434bc2275fc9bab85f82640a19130 -->
- **Maximum Sequence Length:** 384 tokens
- **Output Dimensionality:** 768 dimensions
- **Similarity Function:** Cosine Similarity
- **Supported Modality:** Text
<!-- - **Training Dataset:** Unknown -->
<!-- - **Language:** Unknown -->
<!-- - **License:** Unknown -->

### Model Sources

- **Documentation:** [Sentence Transformers Documentation](https://sbert.net)
- **Repository:** [Sentence Transformers on GitHub](https://github.com/huggingface/sentence-transformers)
- **Hugging Face:** [Sentence Transformers on Hugging Face](https://huggingface.co/models?library=sentence-transformers)

### Full Model Architecture

```
SentenceTransformer(
  (0): Transformer({'transformer_task': 'feature-extraction', 'modality_config': {'text': {'method': 'forward', 'method_output_name': 'last_hidden_state'}}, 'module_output_name': 'token_embeddings', 'architecture': 'MPNetModel'})
  (1): Pooling({'embedding_dimension': 768, 'pooling_mode': 'mean', 'include_prompt': True})
  (2): Normalize({})
)
```

## Usage

### Direct Usage (Sentence Transformers)

First install the Sentence Transformers library:

```bash
pip install -U sentence-transformers
```
Then you can load this model and run inference.
```python
from sentence_transformers import SentenceTransformer

# Download from the 🤗 Hub
model = SentenceTransformer("sentence_transformers_model_id")
# Run inference
sentences = [
    'Statistical Researcher with 2 years working across active teams. Demonstrated technical execution and history background includes: Theoretical knowledge of Python3, Academic projects utilizing PostgreSQL, Basic understanding of Statistical Modeling. Seeking an engineering position to scale architectural patterns.',
    'We are looking for a Lead Product Analyst with a minimum of 7+ years of experience. The core technical stack requirements involve deep knowledge in: Python, Postgres, Machine Learning, GenAI, AWS Cloud Platform. Must be highly capable of executing product deliverables in a fast paced workspace environment.',
    'Seeking a skilled Distributed Systems Software Architect to join our growing team. Key responsibilities include designing high-throughput message brokers and backend streaming infrastructures. Must be fully comfortable handling tools like Java, Spring Boot framework, microservices decoupling, and Apache Kafka streams in a fast-paced environment.',
]
embeddings = model.encode(sentences)
print(embeddings.shape)
# [3, 768]

# Get the similarity scores for the embeddings
similarities = model.similarity(embeddings, embeddings)
print(similarities)
# tensor([[1.0000, 0.2561, 0.1179],
#         [0.2561, 1.0000, 0.6397],
#         [0.1179, 0.6397, 1.0000]])
```
<!--
### Direct Usage (Transformers)

<details><summary>Click to see the direct usage in Transformers</summary>

</details>
-->

<!--
### Downstream Usage (Sentence Transformers)

You can finetune this model on your own dataset.

<details><summary>Click to expand</summary>

</details>
-->

<!--
### Out-of-Scope Use

*List how the model may foreseeably be misused and address what users ought not to do with the model.*
-->

## Evaluation

### Metrics

#### Semantic Similarity

* Dataset: `ats-val`
* Evaluated with [<code>EmbeddingSimilarityEvaluator</code>](https://sbert.net/docs/package_reference/sentence_transformer/evaluation.html#sentence_transformers.sentence_transformer.evaluation.EmbeddingSimilarityEvaluator)

| Metric              | Value      |
|:--------------------|:-----------|
| pearson_cosine      | 0.8695     |
| **spearman_cosine** | **0.8368** |

<!--
## Bias, Risks and Limitations

*What are the known or foreseeable issues stemming from this model? You could also flag here known failure cases or weaknesses of the model.*
-->

<!--
### Recommendations

*What are recommendations with respect to the foreseeable issues? For example, filtering explicit content.*
-->

## Training Details

### Training Dataset

#### Unnamed Dataset

* Size: 350 training samples
* Columns: <code>sentence_0</code>, <code>sentence_1</code>, and <code>label</code>
* Approximate statistics based on the first 100 samples:
  |          | sentence_0                                                                         | sentence_1                                                                         | label                                                           |
  |:---------|:-----------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------|:----------------------------------------------------------------|
  | type     | string                                                                             | string                                                                             | float                                                           |
  | modality | text                                                                               | text                                                                               |                                                                 |
  | details  | <ul><li>min: 39 tokens</li><li>mean: 56.66 tokens</li><li>max: 72 tokens</li></ul> | <ul><li>min: 59 tokens</li><li>mean: 66.74 tokens</li><li>max: 76 tokens</li></ul> | <ul><li>min: 0.0</li><li>mean: 0.54</li><li>max: 0.95</li></ul> |
* Samples:
  | sentence_0                                                                                                                                                                                                                                                                                                                                                                            | sentence_1                                                                                                                                                                                                                                                                                                                                                                                     | label               |
  |:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:--------------------|
  | <code>Modern JavaScript Systems Engineer bringing over 14 years of industry experience along with a verified Masters degree. Expert competencies cover React ecosystem paradigms, state containers, asynchronous fetch flows, and responsive patterns. Proven success track record in abstracting core layout state patterns into reusable, contextually driven modular hooks.</code> | <code>Seeking a skilled Mobile UI App Lead to join our growing team. Key responsibilities include optimizing responsive visual components to enforce smooth multi-device execution footprints. Must be fully comfortable handling tools like JavaScript/TypeScript mobile modules, cross-platform view systems, and offline sync mechanics in a fast-paced environment.</code>                 | <code>0.9229</code> |
  | <code>Senior Frontend Engineer bringing over 10 years of industry experience along with a verified Bachelors degree. Expert competencies cover Redux Toolkit, Webpack, JavaScript, and HTML5/CSS3. Proven success track record in building highly interactive web user interfaces and dashboard layouts.</code>                                                                       | <code>Seeking a skilled Deep Learning Scientist to join our growing team. Key responsibilities include building real-time feature stores and tracking continuous inference degradation. Must be fully comfortable handling tools like LLM Fine-Tuning pipelines, Hugging Face Transformers, and Vector DB architectures in a fast-paced environment.</code>                                    | <code>0.2105</code> |
  | <code>Lead Data Scientist bringing over 14 years of industry experience along with a verified Masters degree. Expert competencies cover Time-series forecasting models, advanced regression tracking, and stochastic modeling matrices. Proven success track record in extracting predictive features from massive volatile event tracking logs.</code>                               | <code>Seeking a skilled Algo-Trading Research Associate to join our growing team. Key responsibilities include running complex mathematical optimization simulations across multivariable risk matrix portfolios. Must be fully comfortable handling tools like Stochastic calculus integrations, Monte Carlo simulations, and historical backtesting data in a fast-paced environment.</code> | <code>0.9511</code> |
* Loss: [<code>CosineSimilarityLoss</code>](https://sbert.net/docs/package_reference/sentence_transformer/losses.html#cosinesimilarityloss) with these parameters:
  ```json
  {
      "loss_fct": "torch.nn.modules.loss.MSELoss",
      "cos_score_transformation": "torch.nn.modules.linear.Identity"
  }
  ```

### Training Hyperparameters
#### Non-Default Hyperparameters

- `per_device_train_batch_size`: 16
- `num_train_epochs`: 10
- `fp16`: True
- `per_device_eval_batch_size`: 16
- `multi_dataset_batch_sampler`: round_robin

#### All Hyperparameters
<details><summary>Click to expand</summary>

- `per_device_train_batch_size`: 16
- `num_train_epochs`: 10
- `max_steps`: -1
- `learning_rate`: 5e-05
- `lr_scheduler_type`: linear
- `lr_scheduler_kwargs`: None
- `warmup_steps`: 0
- `optim`: adamw_torch_fused
- `optim_args`: None
- `weight_decay`: 0.0
- `adam_beta1`: 0.9
- `adam_beta2`: 0.999
- `adam_epsilon`: 1e-08
- `optim_target_modules`: None
- `gradient_accumulation_steps`: 1
- `average_tokens_across_devices`: True
- `max_grad_norm`: 1
- `label_smoothing_factor`: 0.0
- `bf16`: False
- `fp16`: True
- `bf16_full_eval`: False
- `fp16_full_eval`: False
- `tf32`: None
- `gradient_checkpointing`: False
- `gradient_checkpointing_kwargs`: None
- `torch_compile`: False
- `torch_compile_backend`: None
- `torch_compile_mode`: None
- `use_liger_kernel`: False
- `liger_kernel_config`: None
- `use_cache`: False
- `neftune_noise_alpha`: None
- `torch_empty_cache_steps`: None
- `auto_find_batch_size`: False
- `log_on_each_node`: True
- `logging_nan_inf_filter`: True
- `include_num_input_tokens_seen`: no
- `log_level`: passive
- `log_level_replica`: warning
- `disable_tqdm`: False
- `project`: huggingface
- `trackio_space_id`: None
- `trackio_bucket_id`: None
- `trackio_static_space_id`: None
- `per_device_eval_batch_size`: 16
- `prediction_loss_only`: True
- `eval_on_start`: False
- `eval_do_concat_batches`: True
- `eval_use_gather_object`: False
- `eval_accumulation_steps`: None
- `include_for_metrics`: []
- `batch_eval_metrics`: False
- `save_only_model`: False
- `save_on_each_node`: False
- `enable_jit_checkpoint`: False
- `push_to_hub`: False
- `hub_private_repo`: None
- `hub_model_id`: None
- `hub_strategy`: every_save
- `hub_always_push`: False
- `hub_revision`: None
- `load_best_model_at_end`: False
- `ignore_data_skip`: False
- `restore_callback_states_from_checkpoint`: False
- `full_determinism`: False
- `seed`: 42
- `data_seed`: None
- `use_cpu`: False
- `accelerator_config`: {'split_batches': False, 'dispatch_batches': None, 'even_batches': True, 'use_seedable_sampler': True, 'non_blocking': False, 'gradient_accumulation_kwargs': None}
- `parallelism_config`: None
- `dataloader_drop_last`: False
- `dataloader_num_workers`: 0
- `dataloader_pin_memory`: True
- `dataloader_persistent_workers`: False
- `dataloader_prefetch_factor`: None
- `remove_unused_columns`: True
- `label_names`: None
- `train_sampling_strategy`: random
- `length_column_name`: length
- `ddp_find_unused_parameters`: None
- `ddp_bucket_cap_mb`: None
- `ddp_broadcast_buffers`: False
- `ddp_static_graph`: None
- `ddp_backend`: None
- `ddp_timeout`: 1800
- `fsdp`: None
- `fsdp_config`: None
- `deepspeed`: None
- `debug`: []
- `skip_memory_metrics`: True
- `do_predict`: False
- `resume_from_checkpoint`: None
- `warmup_ratio`: None
- `local_rank`: -1
- `prompts`: None
- `batch_sampler`: batch_sampler
- `multi_dataset_batch_sampler`: round_robin
- `router_mapping`: {}
- `learning_rate_mapping`: {}

</details>

### Training Logs
| Epoch | Step | ats-val_spearman_cosine |
|:-----:|:----:|:-----------------------:|
| 1.0   | 22   | 0.5240                  |
| 2.0   | 44   | 0.7356                  |
| 3.0   | 66   | 0.7751                  |
| 4.0   | 88   | 0.8333                  |
| 5.0   | 110  | 0.8272                  |
| 6.0   | 132  | 0.8317                  |
| 7.0   | 154  | 0.8167                  |
| 8.0   | 176  | 0.8305                  |
| 9.0   | 198  | 0.8368                  |


### Training Time
- **Training**: 1.0 minutes

### Framework Versions
- Python: 3.12.13
- Sentence Transformers: 5.6.0
- Transformers: 5.13.1
- PyTorch: 2.11.0+cu128
- Accelerate: 1.14.0
- Datasets: 4.0.0
- Tokenizers: 0.22.2

## Citation

### BibTeX

#### Sentence Transformers
```bibtex
@inproceedings{reimers-2019-sentence-bert,
    title = "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks",
    author = "Reimers, Nils and Gurevych, Iryna",
    booktitle = "Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing",
    month = "11",
    year = "2019",
    publisher = "Association for Computational Linguistics",
    url = "https://arxiv.org/abs/1908.10084",
}
```

<!--
## Glossary

*Clearly define terms in order to be accessible across audiences.*
-->

<!--
## Model Card Authors

*Lists the people who create the model card, providing recognition and accountability for the detailed work that goes into its construction.*
-->

<!--
## Model Card Contact

*Provides a way for people who have updates to the Model Card, suggestions, or questions, to contact the Model Card authors.*
-->