<?php

namespace App\Http\Requests\Resource;

use Illuminate\Foundation\Http\FormRequest;
use App\Enums\ResourceType;

class ResourceFilterRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'is_paginate'     => ['nullable', 'boolean'],
            'count_item'      => ['nullable', 'integer'],
            'resource_name'   => ['nullable', 'string'],
            'resource_type'   => ['nullable', 'in:' . implode(',', ResourceType::values())],
        ];
    }

    public function messages(): array
    {
        return [
            'resource_type.in'       => 'نوع منبع معتبر نیست.',
            'resource_name.string'   => 'نام منبع باید متن باشد.',
        ];
    }
}
