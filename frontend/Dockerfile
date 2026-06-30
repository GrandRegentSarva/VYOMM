FROM node:22-alpine

WORKDIR /app

COPY frontend/package*.json /app/
RUN npm ci

COPY frontend /app

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--port", "5173"]
