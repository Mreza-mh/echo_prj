
import { HttpInterceptorFn, HttpRequest, HttpHandler, HttpEvent, HttpErrorResponse } from '@angular/common/http';
import { throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { Router } from '@angular/router';
import { inject } from '@angular/core';

export const errorHandlerInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      
      console.error('HTTP Error:', error);

      let errorMessage = getErrorMessage(error);

      // Redirect to login on 401 Unauthorized
      if (error.status === 401) {
        router.navigate(['/auth/login']);
      }

      return throwError(() => new Error(errorMessage));
    })
  );
};

function getErrorMessage(error: HttpErrorResponse): string {
  if (error.error instanceof ErrorEvent) {
    // Client-side error
    return `${error.error.message}`;
  } else {
    // Server-side error
    console.log('Server Error:', error);

    switch (error.status) {
      case 400:
        return error.error.message || 'ارور در داده ی ورودی';
      case 401:
        return'سطح دسترسی غیر مجاز';
      case 404:
        return 'صحفه یا داده ی مورد نظر یافت نشد';
      case 422:
        // If errors are an array, join them into a string
        return Array.isArray(error.error.errors)
          ? error.error.errors.join(', ')
          : error.error.errors || 'مشکل در اعتبارسنجی داده ه';
      default:
        return 'خطای ناشناخته';
    }
  }
}