<?php

namespace App\Http\Requests\Staff;

use App\Enums\StaffRoleType;
use App\Enums\UserRole;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Contracts\Validation\Validator;
use Illuminate\Http\Exceptions\HttpResponseException;
use Illuminate\Validation\Rule;

class StaffFilterRequest extends FormRequest
{
    protected $stopOnFirstFailure = true;
    public function authorize()
    {
        return true;
    }
    protected function failedValidation(Validator $validator)
    {
        $errorMessage = $validator->errors()->first();
        throw new HttpResponseException(response()->json(['message' => $errorMessage,'success' => false], 400));
    }
    public function rules(): array
    {
        return [
            'is_paginate'     => ['nullable', 'boolean'],
            'count_item'      => ['nullable', 'integer'],
            'expertise_id'    => ['nullable', 'integer', 'exists:expertises,id'],
            'day' => ['nullable', 'in:sat,sun,mon,tue,wed,thu,fri'],
        ];
    }

    public function messages(): array
    {
        return [
            'expertise_id.integer'   => 'شناسه تخصص باید عدد باشد.',
            'expertise_id.exists'    => 'تخصص انتخاب شده معتبر نیست.',
            'day.in'              => 'روز وارد شده معتبر نیست.',
        ];
    }
}
