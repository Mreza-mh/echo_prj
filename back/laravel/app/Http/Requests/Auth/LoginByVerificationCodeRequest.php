<?php

namespace App\Http\Requests\Auth;

use Illuminate\Contracts\Validation\Validator;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Http\Exceptions\HttpResponseException;

class LoginByVerificationCodeRequest extends FormRequest
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
            response()->json(['message' => $errorMessage, 'success' => false], 400)
        );
    }

    public function rules(): array
    {
        return [
            'email' => ['required', 'email'],
            'verification_code' => ['required', 'digits:5']
        ];
    }

    public function messages(): array
    {
        return [
            //'email.required' => 'ایمیل وارد نشده است',
            //'email.email' => 'فرمت ایمیل معتبر نیست',

            'verification_code.required' => 'کد تایید وارد نشده است',
            'verification_code.digits' => 'کد تایید باید ۵ رقم باشد',
        ];
    }
}
