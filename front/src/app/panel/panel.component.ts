import { Component, OnInit, inject, ViewChild, DestroyRef } from '@angular/core';
import { Router, RouterModule, ActivatedRoute } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule, MatSidenav } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatChipsModule } from '@angular/material/chips';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { TranslationService } from '../@shared/services/translation.service';
import { ThemeService } from '../@shared/services/theme.service';
import { PanelService } from './panel.service';
import { Observable, map, shareReplay, filter, take } from 'rxjs';

@Component({
  selector: 'app-panel',
  standalone: true,
  imports: [
    RouterModule,
    CommonModule,
    MatToolbarModule,
    MatSidenavModule,
    MatListModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatDividerModule,
    MatExpansionModule,
    MatTooltipModule,
    MatChipsModule,
  ],
  templateUrl: './panel.component.html',
  styleUrl: './panel.component.scss',
})
export class PanelComponent implements OnInit {
  @ViewChild('sidenav') sidenav!: MatSidenav;

  isMobile = false;
  sidenavOpened = true;
  sidebarCollapsed = false;

  // Data from PanelService
  currentUser$: Observable<any>;
  activeOrganization$: Observable<any>;

  private breakpointObserver = inject(BreakpointObserver);
  public translationService = inject(TranslationService);
  private themeService = inject(ThemeService);
  private panelService = inject(PanelService);
  private router = inject(Router);
  private activatedRoute = inject(ActivatedRoute);
  private destroyRef = inject(DestroyRef);

  isHandset$: Observable<boolean> = this.breakpointObserver.observe(Breakpoints.Handset).pipe(
    map((result) => result.matches),
    shareReplay()
  );

  constructor() {
    this.currentUser$ = this.panelService.currentUser$;
    this.activeOrganization$ = this.panelService.activeOrganization$;
  }

  ngOnInit() {
    this.isHandset$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(isHandset => {
      this.isMobile = isHandset;
      if (isHandset) {
        this.sidenavOpened = false;
      } else {
        this.sidenavOpened = true;
      }
    });

    // Handle query params for organization persistence
    this.activatedRoute.queryParams.pipe(
      filter(params => params['orgId']),
      take(1),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe(params => {
      const orgId = params['orgId'];
      // We'll set a placeholder to tell getMe which org to prefer
      this.panelService.setActiveOrganization({ id: orgId });
    });

    // Load initial user data
    this.panelService.getMe().pipe(takeUntilDestroyed(this.destroyRef)).subscribe(response => {
      if (response.success && response.data) {
        // Update URL if needed
        const currentOrgId = this.panelService.getActiveOrganizationId();
        if (currentOrgId) {
          this.updateUrl(currentOrgId);
        }
      }
    });
  }

  toggleSidenav() {
    this.sidenavOpened = !this.sidenavOpened;
    if (this.isMobile && this.sidenavOpened) {
      this.sidenav?.open();
    } else if (this.isMobile && !this.sidenavOpened) {
      this.sidenav?.close();
    }
    
    if (!this.sidenavOpened) {
      this.sidebarCollapsed = false;
    }
  }

  toggleSidebarCollapse(): void {
    if (!this.sidenavOpened) return;
    this.sidebarCollapsed = !this.sidebarCollapsed;
  }

  closeSidenav() {
    if (this.isMobile) {
      this.sidenavOpened = false;
      this.sidenav?.close();
    }
  }

  toggleTheme() {
    this.themeService.toggleTheme();
  }

  get isDarkMode(): boolean {
    return this.themeService.getCurrentTheme();
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  switchOrganization(org: any): void {
    this.panelService.setActiveOrganization(org);
    this.updateUrl(org.id);
    // Refresh current route or dashboard
    this.router.navigate(['/panel/dashboard'], { queryParams: { orgId: org.id } });
  }

  private updateUrl(orgId: string): void {
    this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { orgId: orgId },
      queryParamsHandling: 'merge',
      replaceUrl: true
    });
  }

  logout(): void {
    // Implement logout logic
    localStorage.clear();
    this.router.navigate(['/auth/login']);
  }
}
