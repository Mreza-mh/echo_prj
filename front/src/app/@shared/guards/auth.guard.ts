import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { CredentialsService } from '../../auth/credentials.service';


export const authGuard: CanActivateFn = (route, state) => {
  const credentialsService = inject(CredentialsService);
  const router = inject(Router);

  const requiredRoles = route.data?.['roles'] as string[] | undefined;

  if (!credentialsService.isAuthenticated()) {
    router.navigate(['/auth/login'], { queryParams: { returnUrl: state.url } });
    return false;
  }

  // بررسی نقش در صورت نیاز
  if (requiredRoles && !credentialsService.checkHasOneRole(requiredRoles)) {
    // اگر نقش نداشت، اجازه عبور نده
    router.navigate(['/404']);
    return false;
  }

  return true;
};
