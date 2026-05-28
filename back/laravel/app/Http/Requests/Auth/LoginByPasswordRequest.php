<?php

namespace App\Http\Requests\Auth;

use Illuminate\Contracts\Validation\Validator;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Http\Exceptions\HttpResponseException;

class LoginByPasswordRequest extends FormRequest
{
    protected $stopOnFirstFailure = true;

    public function authorize(): bool
    {
        return true;
    }

    protected function failedValidation(Validator $validator)
    {
        $errorMessage = $validator->errors()->first();
        throw new HttpResponseException(
            response()->json(['message' => $errorMessage], 400)
        );
    }

    public function rules(): array
    {
        return [
            'email' => ['required', 'email'],
            'password' => [
                'required',
            ],
        ];
    }

    public function messages(): array
    {
        return [
            'email.required' => 'ایمیل وارد نشده است',
            'email.email' => 'فرمت ایمیل معتبر نیست',

            'password.required' => 'گذرواژه وارد نشده است',
        ];
    }
}
