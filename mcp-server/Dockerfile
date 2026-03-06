FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci || npm install

COPY . .
RUN npm run build

EXPOSE 8000

CMD ["node", "dist/index.js"]
