FROM php:8.2-apache

# نصب پیش‌نیازهای لاراول
RUN apt-get update && apt-get install -y \
    libpng-dev libonig-dev libxml2-dev zip unzip git curl

# نصب اکستنشن‌های PHP
RUN docker-php-ext-install pdo_mysql mbstring exif pcntl bcmath gd

# فعال کردن مد ری‌رایت آپاچی
RUN a2enmod rewrite

# کپی کردن کدها به کانتینر
COPY . /var/www/html

# تنظیم دسترسی‌های لاراول
RUN chown -R www-data:www-data /var/www/html/storage /var/www/html/bootstrap/cache

WORKDIR /var/www/html

# پورت پیش‌فرض آپاچی
EXPOSE 80
