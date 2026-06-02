<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

class AuthenticateFileAccess
{
    /**
     * Handle an incoming request.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  \Closure  $next
     * @return mixed
     */
    public function handle(Request $request, Closure $next)
    {
        // اول سعی کنیم با Bearer Token احراز هویت کنیم
        if ($request->bearerToken()) {
            $guard = Auth::guard('api');
            if ($guard->check()) {
                return $next($request);
            }
        }

        // اگر Bearer Token نداشت، سعی کنیم با Session احراز هویت کنیم
        if (Auth::guard('web')->check()) {
            return $next($request);
        }

        // اگر هیچ کدام کار نکرد، دسترسی عمومی به تصاویر
        // (یا می‌توانید 403 برگردانید)
        return $next($request);
    }
}
