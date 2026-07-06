<?php

namespace App\Logging;

use Illuminate\Log\Logger;
use Monolog\Formatter\LineFormatter;

class CleanLineFormatter
{
    /**
     * فرمت خط لاگ را به «[تاریخ ساعت] پیام» ساده می‌کند، بدون channel/level/context اضافه.
     * لاراول این تابع را با نمونه‌ای از Illuminate\Log\Logger صدا می‌زند، نه Monolog\Logger خام.
     */
    public function __invoke(Logger $logger): void
    {
        $logger = $logger->getLogger();
        $formatter = new LineFormatter("[%datetime%] %message%\n", 'Y-m-d H:i:s', true, true);

        foreach ($logger->getHandlers() as $handler) {
            $handler->setFormatter($formatter);
        }
    }
}
