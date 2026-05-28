import { Injectable, OnDestroy } from '@angular/core';
import { Observable, BehaviorSubject, of, Subscription } from 'rxjs';
import { map, catchError, switchMap, finalize } from 'rxjs/operators';
import { Router } from '@angular/router';
import { CredentialsService } from './credentials.service';
import { AuthHTTPService } from './auth-http.service';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  constructor(
    private authHttpService: AuthHTTPService,
    private credentialsService: CredentialsService,
    private router: Router,
  ) {}

  // confirm(context: any): any {
  //   return this.authHttpService.confirmMobile(context).pipe(
  //     map((auth: any) => {
  //       // console.log("salam bar contex :",context);
  //       // console.log("salam bar auth :",auth);
  //       var token = {
  //         mobile: auth.mobile,
  //         token: auth.token,
  //       };
  //       this.credentialsService.setCredentials(token, context.remember);
  //       return token;
  //     })
  //   );
  // }

  confirmCode(content: any): Observable<any> {
    return this.authHttpService.loginWithSms(content).pipe(
      map((auth: any) => {
        console.log('auth : ' + auth);
        var token = {
          email: auth.data.user.email,
          token: auth.data.token,
        };
        console.log('auth', token);
        this.credentialsService.setCredentials(token, true);

        var componentInfo = {
          message: auth.message,
          success: auth.success,
          id: auth.data.id,
          temporary_token: auth.data.temporary_token,
        };
        return componentInfo;
      }),
    );
  }

  loginPassword(context: any): any {
    return this.authHttpService.loginPassword(context).pipe(
      map((auth: any) => {
        console.log(auth);

        var token = {
          email: auth.data.user.email,
          token: auth.data.token,
        };
        var componentInfo = {
          message: auth.message,
          success: auth.success,
        };
        this.credentialsService.setCredentials(token, true);
        return componentInfo;
      }),
    );
  }

  /**
   * Logs out the user and clear credentials.
   * @return True if the user was logged out successfully.
   */
  logout(): Observable<boolean> {
    // Customize credentials invalidation here
    this.credentialsService.setCredentials();
    return of(true);
  }

  private userRoleSubject = new BehaviorSubject<string | null>(null);
  userRole$ = this.userRoleSubject.asObservable();

  getUserInfo(): Observable<any> {
    return this.authHttpService.getMe().pipe(
      map((resp: any) => {
        if (resp && resp.success && resp.data) {
          this.userRoleSubject.next(resp.data.role);
        }
        return resp;
      }),
    );
  }

  verifyToken(): any {
    if (!this.credentialsService.isAuthenticated()) {
      return of(undefined);
    }
    return this.getUserInfo();
  }

  passwordStatus = new BehaviorSubject<boolean>(false);

  set setPasswordStatus(status: boolean) {
    this.passwordStatus.next(status);
  }
  get getPasswordStatus() {
    return this.passwordStatus.asObservable();
  }
}
