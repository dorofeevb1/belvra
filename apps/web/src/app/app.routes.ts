import { Routes } from '@angular/router';
import { authGuard, masterGuard, clientGuard, guestGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    redirectTo: 'login',
    pathMatch: 'full'
  },
  {
    path: 'login',
    canActivate: [guestGuard],
    loadComponent: () => import('./features/auth/login/login.component').then(m => m.LoginComponent)
  },
  {
    path: 'register',
    canActivate: [guestGuard],
    loadComponent: () => import('./features/auth/register/register.component').then(m => m.RegisterComponent)
  },
  {
    path: 'forgot-password',
    canActivate: [guestGuard],
    loadComponent: () => import('./features/auth/forgot-password/forgot-password.component').then(m => m.ForgotPasswordComponent)
  },
  {
    path: 'reset-password',
    canActivate: [guestGuard],
    loadComponent: () => import('./features/auth/reset-password/reset-password.component').then(m => m.ResetPasswordComponent)
  },
  {
    path: 'verify-email',
    loadComponent: () => import('./features/auth/verify-email/verify-email.component').then(m => m.VerifyEmailComponent)
  },
  {
    path: 'master',
    canActivate: [masterGuard],
    loadComponent: () => import('./features/master/master-view.component').then(m => m.MasterViewComponent),
    children: [
      {
        path: '',
        redirectTo: 'dashboard',
        pathMatch: 'full'
      },
      {
        path: 'dashboard',
        loadComponent: () => import('./features/master/dashboard/dashboard.component').then(m => m.DashboardComponent)
      },
      {
        path: 'calendar',
        loadComponent: () => import('./features/master/calendar/calendar.component').then(m => m.CalendarComponent)
      },
      {
        path: 'kanban',
        loadComponent: () => import('./features/master/calendar/kanban-board.component').then(m => m.KanbanBoardComponent)
      },
      {
        path: 'appointments',
        loadComponent: () => import('./features/master/appointments/appointments.component').then(m => m.AppointmentsComponent)
      },
      {
        path: 'portfolio',
        loadComponent: () => import('./features/master/portfolio/portfolio.component').then(m => m.PortfolioComponent)
      },
      {
        path: 'chat',
        loadComponent: () => import('./features/master/chat/chat.component').then(m => m.ChatComponent)
      },
      {
        path: 'finances',
        loadComponent: () => import('./features/master/finances/finances.component').then(m => m.FinancesComponent)
      },
      {
        path: 'settings',
        loadComponent: () => import('./features/master/settings/settings.component').then(m => m.SettingsComponent)
      },
      {
        path: 'subscription',
        loadComponent: () => import('./features/master/subscription/subscription.component').then(m => m.SubscriptionComponent)
      }
    ]
  },
  {
    path: 'client',
    canActivate: [clientGuard],
    loadComponent: () => import('./features/client/client-view.component').then(m => m.ClientViewComponent),
    children: [
      {
        path: '',
        loadComponent: () => import('./features/client/search/master-search.component').then(m => m.MasterSearchComponent)
      },
      {
        path: 'master/:id',
        loadComponent: () => import('./features/client/master-profile/master-profile.component').then(m => m.MasterProfileComponent)
      },
      {
        path: 'booking/:masterId',
        loadComponent: () => import('./features/client/booking/booking-calendar.component').then(m => m.BookingCalendarComponent)
      },
      {
        path: 'my-appointments',
        loadComponent: () => import('./features/client/my-appointments/my-appointments.component').then(m => m.MyAppointmentsComponent)
      },
      {
        path: 'chat',
        loadComponent: () => import('./features/client/chat/client-chat.component').then(m => m.ClientChatComponent)
      },
      {
        path: 'favorites',
        loadComponent: () => import('./features/client/favorites/favorites.component').then(m => m.FavoritesComponent)
      },
      {
        path: 'profile',
        loadComponent: () => import('./features/client/profile/client-profile.component').then(m => m.ClientProfileComponent)
      },
      {
        path: 'subscription',
        loadComponent: () => import('./features/client/subscription/subscription.component').then(m => m.ClientSubscriptionComponent)
      }
    ]
  },
  {
    path: '**',
    redirectTo: 'login'
  }
];
