<?php

namespace App\Enums;

enum ResourceType: string
{
    case room = 'room';
    case device = 'device';
    case equipment = 'equipment';
    case other = 'other';

    public static function values(): array
    {
        return array_column(self::cases(), 'value');
    }

}
