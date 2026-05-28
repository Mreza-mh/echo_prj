<?php

namespace App\Enums;

enum SettingKey:string
{
    case login_method = 'login_method';
    case site_title = 'site_title';
    case general_commissions = 'general_commissions';
}
