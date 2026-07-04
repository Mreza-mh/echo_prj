<?php

namespace App\Logging;

use Monolog\Formatter\LineFormatter;
use Monolog\Logger;

class CleanLineFormatter
{
    /**
     * فرمت خط لاگ را به «[تاریخ ساعت] پیام» ساده می‌کند، بدون channel/level/context اضافه.
     */
    public function __invoke(Logger $logger): void
    {
        $formatter = new LineFormatter("[%datetime%] %message%\n", 'Y-m-d H:i:s', true, true);

        foreach ($logger->getHandlers() as $handler) {
            $handler->setFormatter($formatter);
        }
    }
}
