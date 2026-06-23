# 旅行助手 前端 Docker 镜像
FROM node:24-alpine

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend ./
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
