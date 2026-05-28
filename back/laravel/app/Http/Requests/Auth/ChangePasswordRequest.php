<?php

namespace App\Http\Requests\Auth;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Contracts\Validation\Validator;
use Illuminate\Http\Exceptions\HttpResponseException;
class ChangePasswordRequest extends FormRequest
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
            'current_password' => 'required|string|min:6',
            'new_password' => 'required|string|min:6|confirmed',
            'new_password_confirmation' => 'required|string|min:6'
        ];
    }

    public function messages(): array
    {
        return [
            'current_password.required' => 'رمز عبور فعلی الزامی است',
            'current_password.min' => 'رمز عبور فعلی باید حداقل ۶ کاراکتر باشد',
            'new_password.required' => 'رمز عبور جدید الزامی است',
            'new_password.min' => 'رمز عبور جدید باید حداقل ۶ کاراکتر باشد',
            'new_password.confirmed' => 'رمز عبور جدید با تکرار آن مطابقت ندارد',
            'new_password_confirmation.required' => 'تکرار رمز عبور جدید الزامی است',
            'new_password_confirmation.min' => 'تکرار رمز عبور جدید باید حداقل ۶ کاراکتر باشد'
        ];
    }
} 