FROM python:3.11-slim

WORKDIR /app

# 复制项目文件
COPY pyproject.toml .
COPY src/ src/

# 安装依赖
RUN pip install --no-cache-dir .

# 复制配置
COPY .agent.yaml .

# 创建工作区挂载点
RUN mkdir -p /workspace

WORKDIR /workspace

ENTRYPOINT ["python", "-m", "agent"]
