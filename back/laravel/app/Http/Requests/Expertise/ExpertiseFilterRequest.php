<?php

namespace App\Http\Requests\Expertise;

use Illuminate\Foundation\Http\FormRequest;

class ExpertiseFilterRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'is_paginate' => ['nullable', 'boolean'],
            'count_item'  => ['nullable', 'integer'],
            'title'       => ['nullable', 'string'],
            'label'       => ['nullable', 'string'],
        ];
    }

    public function messages(): array
    {
        return [
            'title.string' => 'عنوان انگلیسی باید متن باشد.',
            'label.string' => 'عنوان فارسی باید متن باشد.',
        ];
    }
}
