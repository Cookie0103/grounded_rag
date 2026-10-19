Dify 使用默认配置即可开箱即用。如需自定义部署，编辑相关文件中的环境变量：

- **必要的启动值** 位于 `docker/.env` 文件中（部署时从 `docker/.env.example` 复制创建）。直接编辑即可。

- **可选或特定提供商的设置** 在 `docker/envs/` 下有对应模板。要覆盖默认值，复制相应模板（去掉 `.example` 后缀），然后编辑副本。例如：

  ```bash
  cd dify/docker
  cp envs/vectorstores/milvus.env.example envs/vectorstores/milvus.env
  ```

`docker/.env` 中的值优先于任何 `docker/envs/*.env` 文件中的值。

**提示：**
升级 Dify 后，对照各 `.env.example` 文件检查对应的 `.env`，确认是否有新增或变更的变量。

## 通用变量

这些 URL 变量用于配置 Dify 各服务的访问地址。

对于 Nginx 后的单域名部署（默认 Docker Compose 配置），这些变量可以留空，系统会从请求中自动检测。当使用自定义域名、多域名部署或反向代理时，需要配置这些变量。

### CONSOLE_API_URL

默认值：（空）

Dify 后端 API 的公开 URL。如果你使用 OAuth 登录（GitHub、Google）、Notion 集成或任何需要 OAuth 的插件，请设置此变量；这些功能需要绝对回调 URL 才能在授权后将用户重定向回来。此变量还决定是否使用安全（仅 HTTPS）Cookie。

示例：`https://api.console.dify.ai`

### SERVER_CONSOLE_API_URL

默认值：`http://api:5001`

Web 前端容器在服务端发起请求时所使用的 Console API 地址，经由 Docker 内部网络直接访问，而非通过你的公网域名。此变量仅由 Web 前端容器使用，不影响 Python 后端；浏览器端请求仍使用 `CONSOLE_API_URL`。若留空，则回退到 `CONSOLE_API_URL`。仅当 API 服务的内部访问地址不同时才需修改。

### CONSOLE_WEB_URL

### 向量数据库配置

配置用于知识库嵌入存储和相似性搜索的向量数据库。每个提供商有各自的凭证变量，仅配置你使用的那个。

### VECTOR_STORE

默认值：`weaviate`

选择向量数据库后端。如果数据集已有索引，数据集存储的类型优先于此设置。在 Docker Compose 中切换提供商时，`COMPOSE_PROFILES` 会根据此值自动启动匹配的容器。

支持的值：`weaviate`、`oceanbase`、`seekdb`、`qdrant`、`milvus`、`myscale`、`relyt`、`pgvector`、`pgvecto-rs`、`chroma`、`opensearch`、`oracle`、`tencent`、`elasticsearch`、`elasticsearch-ja`、`analyticdb`、`couchbase`、`vikingdb`、`opengauss`、`tablestore`、`vastbase`、`tidb`、`tidb_on_qdrant`、`baidu`、`lindorm`、`huawei_cloud`、`upstash`、`matrixone`、`clickzetta`、`alibabacloud_mysql`、`iris`、`hologres`。

| 变量 | 默认值 | 说明 |
|---|---|---|
| `VECTOR_INDEX_NAME_PREFIX` | `Vector_index` | 向量数据库中集合名称的前缀。如果在多个 Dify 部署间共享向量数据库实例，请更改此值。 |

**Weaviate**

| 变量 | 默认值 | 说明 |
|---|---|---|
| `WEAVIATE_ENDPOINT` | `http://weaviate:8080` | Weaviate REST API 端点。 |
| `WEAVIATE_API_KEY` | （空） | Weaviate 认证的 API key。 |
| `WEAVIATE_GRPC_ENDPOINT` | `grpc://weaviate:50051` | 独立的 gRPC 端点，用于高性能二进制协议。批量操作显著更快。如未设置，将从 HTTP 端点推断。 |
| `WEAVIATE_TOKENIZATION` | `word` | 文本字段的分词方法。选项：`word`（按空格和标点分割）、`whitespace`（仅按空格分割）、`character`（字符级别，更适合中日韩语言）。 |

**OceanBase / seekdb**

seekdb 是 OceanBase 的轻量版本，共享相同的连接配置。

| 变量 | 默认值 | 说明 |
|---|---|---|
| `OCEANBASE_VECTOR_HOST` | `oceanbase` | 主机名或 IP 地址。 |
| `OCEANBASE_VECTOR_PORT` | `2881` | 端口号。 |
| `OCEANBASE_VECTOR_USER` | `root@test` | 数据库用户名。 |
| `OCEANBASE_VECTOR_PASSWORD` | `difyai123456` | 数据库密码。 |
| `OCEANBASE_VECTOR_DATABASE` | `test` | 数据库名称。 |
| `OCEANBASE_CLUSTER_NAME` | `difyai` | 集群名称（仅 Docker 部署）。 |
| `OCEANBASE_MEMORY_LIMIT` | `6G` | OceanBase 内存限制（仅 Docker 部署）。 |
| `SEEKDB_MEMORY_LIMIT` | `2G` | seekdb 内存限制（仅 Docker 部署）。 |
| `OCEANBASE_ENABLE_HYBRID_SEARCH` | `false` | 启用全文索引用于 BM25 查询，配合向量搜索使用。需要 OceanBase >= 4.3.5.1。启用后需重新创建集合。 |
| `OCEANBASE_FULLTEXT_PARSER` | `ik` | 全文解析器。内置：`ngram`、`beng`、`space`、`ngram2`、`ik`。外部（需要插件）：`japanese_ftparser`、`thai_ftparser`。 |

**Qdrant**

| 变量 | 默认值 | 说明 |
|---|---|---|
| `QDRANT_URL` | `http://qdrant:6333` | Qdrant 端点地址。 |
| `QDRANT_API_KEY` | `difyai123456` | Qdrant API key。 |
| `QDRANT_CLIENT_TIMEOUT` | `20` | 客户端超时（秒）。 |
| `QDRANT_GRPC_ENABLED` | `false` | 启用 gRPC 通信。 |
| `QDRANT_GRPC_PORT` | `6334` | gRPC 端口。 |
| `QDRANT_REPLICATION_FACTOR` | `1` | 每个分片的副本数。 |

**Milvus**

| 变量 | 默认值 | 说明 |
|---|---|---|
| `MILVUS_URI` | `http://host.docker.internal:19530` | Milvus URI。对于 Zilliz Cloud，使用 Public Endpoint。 |
| `MILVUS_DATABASE` | （空） | 数据库名称。 |
| `MILVUS_TOKEN` | （空） | 认证令牌。对于 Zilliz Cloud，使用 API Key。 |
| `MILVUS_USER` | （空） | 用户名。 |
| `MILVUS_PASSWORD` | （空） | 密码。 |
| `MILVUS_ENABLE_HYBRID_SEARCH` | `false` | 启用 BM25 稀疏索引用于全文搜索，配合向量相似性搜索使用。需要 Milvus >= 2.5.0。如果集合在未启用时创建，则需重新创建。 |
| `MILVUS_ANALYZER_PARAMS` | （空） | 文本字段的分析器参数。 |
| `MILVUS_SECURE` | `false` | 为 Milvus 连接启用单向 TLS。启用后，客户端通过 TLS 加密的 gRPC 连接并验证服务器证书。 |
| `MILVUS_SERVER_PEM_PATH` | （空） | 容器内 Milvus 服务器证书（PEM）的路径，在启用 `MILVUS_SECURE` 时用于验证服务器。 |
| `MILVUS_SERVER_NAME` | （空） | 用于验证的服务器名称（TLS SNI，需与证书的 CN 或 SAN 匹配）。设置 `MILVUS_SERVER_PEM_PATH` 时必填。 |

**MyScale**

| 变量 | 默认值 | 说明 |
|---|---|---|
| `MYSCALE_HOST` | `myscale` | MyScale 主机。 |
| `MYSCALE_PORT` | `8123` | MyScale 端口。 |
| `MYSCALE_USER` | `default` | 用户名。 |
| `MYSCALE_PASSWORD` | （空） | 密码。 |
| `MYSCALE_DATABASE` | `dify` | 数据库名称。 |
| `MYSCALE_FTS_PARAMS` | （空） | 全文搜索参数。多语言支持参考。 |
