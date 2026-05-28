import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { CredentialsService } from './credentials.service';

export const customerGuard: CanActivateFn = (route, state) => {
   let credentials : CredentialsService = inject(CredentialsService)
   let router:Router= inject(Router)
   if(credentials.checkHasOneRole(['buyer'])){
    return true
  }
  router.navigate(['/auth/login']);
  return false

};
