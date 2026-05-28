import { Injectable } from '@angular/core';
import { of } from 'rxjs';
import  { jwtDecode } from "jwt-decode";

const credentialsKey = 'credentials';


@Injectable({
  providedIn: 'root',
})
export class CredentialsService {
  private _credentials: any | null = null;

  constructor() {
    const savedCredentials = sessionStorage.getItem(credentialsKey) || localStorage.getItem(credentialsKey);
    if (savedCredentials) {
      this._credentials = JSON.parse(savedCredentials);
    }
  }

  /**
   * Checks is the user is authenticated.
   * @return True if the user is authenticated.
   */
  isAuthenticated(): boolean {
    return !!this.credentials;
  }

  /**
   * Gets the user credentials.
   * @return The user credentials or null if the user is not authenticated.
   */
  get credentials(): any | null {
    return this._credentials;
  }

  /**
   * Sets the user credentials.
   * The credentials may be persisted across sessions by setting the `remember` parameter to true.
   * Otherwise, the credentials are only persisted for the current session.
   * @param credentials The user credentials.
   * @param remember True to remember credentials across sessions.
   */

  setCredentials(credentials?: any, remember?: boolean) {
    this._credentials = credentials || null;

    if (credentials) {
      const storage = remember ? localStorage : sessionStorage;
      storage.setItem(credentialsKey, JSON.stringify(credentials));
    } else {
      sessionStorage.removeItem(credentialsKey);
      localStorage.removeItem(credentialsKey);
    }
  }


  checkHasOneRole(roleList:any){
    const auth = this.credentials;
    if (!auth || !auth.token) {
      return undefined;
    }


    var allExist:boolean=false
     var decodeToken:any = jwtDecode(auth.token);
     if(decodeToken['scopes'] instanceof Array){
      allExist = roleList.some((item:any) => decodeToken['scopes'].includes(item));
     }
     else{
      var selectRole = decodeToken['scopes'].split(",");
      allExist = roleList.some((item:any) => selectRole.includes(item));
     }
     return allExist
  }

  checkHasAllRole(roleList:any){
    const auth = this.credentials;
    if (!auth || !auth.token) {
      return of(undefined);
    }
    var allExist:boolean=false
     var decodeToken:any = jwtDecode(auth.token);
     if(decodeToken['scopes'] instanceof Array){
      allExist = roleList.every((item:any) => decodeToken['scopes'].includes(item));
     }
     else{
      var selectRole = decodeToken['scopes'].split(",");
      allExist = roleList.every((item:any) => selectRole.includes(item));
     }
     return allExist
  }

isAdmin(){
    const auth = this.credentials;
    if (!auth || !auth.token) {
      return of(undefined);
    }
    var isAdmin:boolean=false
     var decodeToken:any = jwtDecode(auth.token);
     if(decodeToken['scopes'] instanceof Array){
       isAdmin = decodeToken['scopes'].some(item => item.includes("admin"));
     }
     else{
      var selectRole = decodeToken['scopes'].split(",");
      isAdmin = selectRole.some((item:any) => item.includes("admin"));
     }

     return isAdmin
   }

   isDoctor(){
    return this.checkHasOneRole(['doctor', 'admin']);
   }

   isNurse(){
    return this.checkHasOneRole(['nurse', 'staff']);
   }

 }
