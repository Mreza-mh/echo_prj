<?php
namespace App\Models;

use App\Enums\UserRole;
use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Laravel\Passport\HasApiTokens;


class User extends Authenticatable
{
    use HasApiTokens;

    protected $fillable = [
        'name',
        'mobile',
        'email',
        'password',
        'birthday',
        'email_verification_code',
        'email_verification_expires_at',
        'email_verified_at',
        'is_verify',
        'role'
    ];

    protected $hidden = [
        'password',
        'remember_token',
        'email_verification_code',
        'email_verification_expires_at',
    ];

    public function appointments(): HasMany
    {
        return $this->hasMany(Appointment::class, 'user_id'); // ← اصلاح شد
    }

    public function staffs(): HasMany
    {
        return $this->hasMany(Staff::class);
    }

    public function getScope()
    {
        if ($this->role && in_array($this->role, UserRole::values())) {
            return [$this->role];
        }
        return [UserRole::user->value];
    }
}

