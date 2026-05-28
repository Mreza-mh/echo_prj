<?php

namespace App\Http\Requests\Expertise;

use Illuminate\Foundation\Http\FormRequest;

class ExpertiseEditRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'title' => ['nullable', 'string', 'max:255'],
            'label' => ['nullable', 'string', 'max:255'],
        ];
    }

    public function messages(): array
    {
        return [
            'title.string'   => 'عنوان باید متن باشد.',
            'title.max'      => 'عنوان نباید بیش از ۲۵۵ کاراکتر باشد.',

            'label.string'   => 'عنوان فارسی باید متن باشد.',
            'label.max'      => 'عنوان فارسی نباید بیش از ۲۵۵ کاراکتر باشد.',
        ];
    }
}
