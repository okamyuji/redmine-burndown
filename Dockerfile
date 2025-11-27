# Redmine Burndown Chart Tool - Dockerfile
# マルチステージビルドで最適化されたDockerイメージ

# ========================================
# Stage 1: Builder
# ========================================
FROM python:3.12-slim AS builder

# 作業ディレクトリを設定
WORKDIR /app

# システムパッケージの更新とビルド依存関係のインストール
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# uvをインストール
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# pyproject.tomlとuv.lockをコピー
COPY pyproject.toml uv.lock* ./

# 依存関係をインストール（--systemでシステムPythonにインストール）
RUN /root/.local/bin/uv pip install --system --no-cache -r pyproject.toml

# ========================================
# Stage 2: Runtime
# ========================================
FROM python:3.12-slim

# メタデータ
LABEL maintainer="redmine-burndown"
LABEL description="Redmine Burndown Chart Tool - Docker Image"
LABEL version="1.3.0"

# 環境変数の設定
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 作業ディレクトリを設定
WORKDIR /app

# 必要最小限のシステムパッケージをインストール
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Builderステージから依存関係とuvをコピー
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /root/.local/bin/uv /usr/local/bin/uv
COPY --from=builder /root/.local/bin/uvx /usr/local/bin/uvx

# アプリケーションコードをコピー
COPY src/ ./src/
COPY templates/ ./templates/
COPY pyproject.toml ./
COPY README.md ./
COPY update_burndown.sh ./
COPY update_burndown_docker.sh ./

# パッケージをインストール（editable modeでインストール）
RUN pip install --no-cache-dir -e .

# 実行権限を付与
RUN chmod +x update_burndown.sh update_burndown_docker.sh

# 出力ディレクトリを作成
RUN mkdir -p /app/output

# ボリュームマウントポイントを定義
VOLUME ["/app/output"]

# エントリーポイントを設定
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]

# デフォルトコマンド（update_burndown_docker.shを実行）
CMD ["./update_burndown_docker.sh"]

