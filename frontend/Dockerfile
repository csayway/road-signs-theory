# Використовуєте легкий веб-сервер Nginx
FROM nginx:alpine

# Копіюєте ваші HTML/CSS/JS файли у стандартну папку Nginx
COPY . /usr/share/nginx/html

# Nginx слухає на порту 80 за замовчуванням
EXPOSE 80

# Запустили Nginx
CMD ["nginx", "-g", "daemon off;"]