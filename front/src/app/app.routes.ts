import { Routes } from '@angular/router';
import { authGuard } from './@shared/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    loadChildren: () => import('./index/index.routes').then((m) => m.routes),
  },
  {
    path: 'panel',
    loadChildren: () => import('./panel/panel.routes').then((m) => m.routes),
    canActivate: [authGuard],
    data: { roles: ['admin', 'super_admin'] },
  },
  {
    path: 'super-panel',
    loadChildren: () => import('./super-panel/super-panel.routes').then((m) => m.routes),
    canActivate: [authGuard],
    data: { roles: ['super_admin'] },
  },
  {
    path: 'dr-panel',
    loadChildren: () => import('./doctor-panel/doctor-panel.routes').then((m) => m.routes),
    canActivate: [authGuard],
    data: { roles: ['admin', 'doctor'] },
  },
  {
    path: 'auth',
    loadChildren: () => import('./auth/auth.routes').then((m) => m.routes),
  },
  {
    path: '**',
    redirectTo: '',
  },
];
