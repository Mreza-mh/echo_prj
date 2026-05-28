import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { AuthHTTPService } from '../auth/auth-http.service';
import { GenericHttpService } from '../@shared/services/generic-http.service';

@Injectable({
  providedIn: 'root',
})
export class PanelService {
  private currentUserSubject = new BehaviorSubject<any>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  private activeOrganizationSubject = new BehaviorSubject<any>(null);
  public activeOrganization$ = this.activeOrganizationSubject.asObservable();

  constructor(
    private authHttpService: AuthHTTPService,
    private genericHttpService: GenericHttpService
  ) {}

  /**
   * Fetch organization details and update active organization
   */
  fetchOrganizationDetails(id: string): Observable<any> {
    return this.genericHttpService.get(`/organization/${id}`).pipe(
      tap({
        next: (response: any) => {
          if (response.success && response.data) {
            this.activeOrganizationSubject.next(response.data);
          }
        },
        error: (err) => {
          console.error('Error fetching organization details:', err);
        }
      })
    );
  }

  /**
   * Fetch current user info including organizations
   */
  getMe(): Observable<any> {
    return this.authHttpService.getMe().pipe(
      tap((response: any) => {
        if (response.success && response.data) {
          this.currentUserSubject.next(response.data);
          
          // Auto-select organization if not already set
          if (!this.activeOrganizationSubject.value && response.data.organizations?.length > 0) {
            this.setActiveOrganization(response.data.organizations[0]);
          }
        }
      })
    );
  }

  /**
   * Set the currently active organization for the admin panel
   */
  setActiveOrganization(org: any): void {
    if (org && org.id) {
      // Set the basic org first so UI has something to show immediately
      this.activeOrganizationSubject.next(org);
      // Then fetch full details
      this.fetchOrganizationDetails(org.id).subscribe();
    } else {
      this.activeOrganizationSubject.next(org);
    }
  }

  /**
   * Get the currently active organization ID
   */
  getActiveOrganizationId(): string | null {
    const activeOrg = this.activeOrganizationSubject.value;
    return activeOrg ? activeOrg.id : null;
  }
  
}
