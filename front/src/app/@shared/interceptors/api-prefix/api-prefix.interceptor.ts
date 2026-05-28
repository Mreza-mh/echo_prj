import { HttpInterceptorFn, HttpRequest, HttpHandler, HttpEvent } from '@angular/common/http';
import { inject } from '@angular/core';
import { Observable } from 'rxjs';
import { CredentialsService } from '../../../auth/credentials.service';
import { environment } from '../../../../environments/environment';

export const apiPrefixInterceptor: HttpInterceptorFn = (req, next) => {
  const isAbsolute = /^(http|https):/i.test(req.url);
  const hasApiPrefix = req.url.startsWith(environment.apiUrl) || req.url.startsWith('/api');
  if (!isAbsolute && !hasApiPrefix) {
    req = req.clone({ url: environment.apiUrl + req.url });
  }

  const credentialsService = inject(CredentialsService);
  const auth = credentialsService?.credentials;
  if (auth?.token) {
    req = req.clone({ headers: req.headers.set('Authorization', `Bearer ${auth.token}`) });
  }

  return next(req);
};
