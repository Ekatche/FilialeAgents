'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import {
  User,
  Mail,
  Bell,
  Shield,
  Save,
  Building2,
  Calendar,
  CheckCircle2,
  XCircle,
  CreditCard,
  Users,
  Globe,
  Loader2
} from 'lucide-react';
import { useState } from 'react';
import { formatDate } from '@/lib/utils';
import { useUserProfile, usePortalInfo, useUserPreferences } from '@/hooks/use-account';

export default function AccountPage() {
  const { user, loading: userLoading, error: userError } = useUserProfile();
  const { portal, loading: portalLoading, error: portalError } = usePortalInfo();
  const { preferences, updatePreferences } = useUserPreferences();

  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const handleSave = async () => {
    setIsSaving(true);
    setSaveMessage(null);

    try {
      // Preferences are already saved to localStorage by the hook
      // Just show success message
      setSaveMessage('Paramètres enregistrés avec succès');
      setTimeout(() => setSaveMessage(null), 3000);
    } catch (err) {
      setSaveMessage('Erreur lors de l\'enregistrement');
    } finally {
      setIsSaving(false);
    }
  };


  // Loading state
  if (userLoading || portalLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-[#FE4D01]" />
      </div>
    );
  }

  // Error state - mais permettre l'accès en mode local
  if ((userError || portalError) && (!user && !portal)) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-zinc-900">Paramètres du compte</h1>
          <p className="text-zinc-600 mt-2">
            Gérez vos préférences et paramètres personnels
          </p>
        </div>
        <Card className="border-orange-200 bg-orange-50">
          <CardContent className="pt-6">
            <p className="text-orange-700">
              Vous n'êtes pas connecté. Veuillez vous connecter pour accéder à vos paramètres.
            </p>
            <div className="mt-4">
              <a href="/login/local" className="text-[#FE4D01] hover:underline">
                Se connecter →
              </a>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-zinc-900">Paramètres du compte</h1>
        <p className="text-zinc-600 mt-2">
          Gérez vos préférences et paramètres personnels
        </p>
      </div>

      {/* Save Success Message */}
      {saveMessage && (
        <Card className="border-green-200 bg-green-50">
          <CardContent className="pt-6">
            <p className="text-green-600 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              {saveMessage}
            </p>
          </CardContent>
        </Card>
      )}

      {/* User Information */}
      <Card className="border-zinc-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="w-5 h-5 text-[#FE4D01]" />
            Informations utilisateur
          </CardTitle>
          <CardDescription>
            Vos informations personnelles
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-zinc-600">Prénom</label>
                <div className="mt-1 text-zinc-900">
                  {user?.first_name || 'Non renseigné'}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-zinc-600">Nom</label>
                <div className="mt-1 text-zinc-900">
                  {user?.last_name || 'Non renseigné'}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-zinc-600 flex items-center gap-2">
                  <Mail className="w-4 h-4" />
                  Email
                </label>
                <div className="mt-1 text-zinc-900">{user?.email}</div>
              </div>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-zinc-600">Rôle</label>
                <div className="mt-1">
                  <Badge
                    variant="outline"
                    className={
                      user?.role === 'admin'
                        ? 'bg-orange-50 text-[#FE4D01] border-orange-200'
                        : 'bg-zinc-50 text-zinc-700 border-zinc-200'
                    }
                  >
                    {user?.role === 'admin' ? 'Administrateur' : 'Membre'}
                  </Badge>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-zinc-600 flex items-center gap-2">
                  <Calendar className="w-4 h-4" />
                  Dernière connexion
                </label>
                <div className="mt-1 text-zinc-900">
                  {user?.last_login
                    ? formatDate(user.last_login)
                    : 'Jamais'}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-zinc-600">Statut</label>
                <div className="mt-1 flex items-center gap-2">
                  {user?.is_active ? (
                    <>
                      <CheckCircle2 className="w-4 h-4 text-green-600" />
                      <span className="text-green-600">Actif</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="w-4 h-4 text-red-600" />
                      <span className="text-red-600">Inactif</span>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* HubSpot Portal Information */}
      <Card className="border-zinc-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="w-5 h-5 text-[#FE4D01]" />
            Informations Organisation
          </CardTitle>
          <CardDescription>
            Détails de votre organisation
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-zinc-600">Nom de l'organisation</label>
                <div className="mt-1 text-zinc-900 font-semibold">
                  {portal?.name}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-zinc-600">Portal ID</label>
                <div className="mt-1 text-zinc-900 font-mono text-sm">
                  {portal?.hubspot_portal_id}
                </div>
              </div>
              {portal?.domain && (
                <div>
                  <label className="text-sm font-medium text-zinc-600 flex items-center gap-2">
                    <Globe className="w-4 h-4" />
                    Domaine
                  </label>
                  <div className="mt-1 text-zinc-900">{portal.domain}</div>
                </div>
              )}
              {portal?.timezone && (
                <div>
                  <label className="text-sm font-medium text-zinc-600">Fuseau horaire</label>
                  <div className="mt-1 text-zinc-900">{portal.timezone}</div>
                </div>
              )}
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-zinc-600">Statut</label>
                <div className="mt-1 flex items-center gap-2">
                  {portal?.is_active ? (
                    <>
                      <CheckCircle2 className="w-4 h-4 text-green-600" />
                      <span className="text-green-600">Actif</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="w-4 h-4 text-red-600" />
                      <span className="text-red-600">Inactif</span>
                    </>
                  )}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-zinc-600">Créé le</label>
                <div className="mt-1 text-zinc-900 text-sm">
                  {portal?.created_at ? formatDate(portal.created_at) : 'N/A'}
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Notifications */}
      <Card className="border-zinc-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="w-5 h-5" />
            Notifications
          </CardTitle>
          <CardDescription>
            Configurez vos préférences de notification
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <label className="text-sm font-medium">Notifications par email</label>
              <p className="text-xs text-zinc-500">
                Recevez des emails pour les mises à jour importantes
              </p>
            </div>
            <Switch
              checked={preferences.email_notifications}
              onCheckedChange={(checked) =>
                updatePreferences({ email_notifications: checked })
              }
            />
          </div>
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <label className="text-sm font-medium">Notifications push</label>
              <p className="text-xs text-zinc-500">
                Recevez des notifications dans votre navigateur
              </p>
            </div>
            <Switch
              checked={preferences.push_notifications}
              onCheckedChange={(checked) =>
                updatePreferences({ push_notifications: checked })
              }
            />
          </div>
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <label className="text-sm font-medium">Rapport hebdomadaire</label>
              <p className="text-xs text-zinc-500">
                Recevez un résumé de votre activité chaque semaine
              </p>
            </div>
            <Switch
              checked={preferences.weekly_report}
              onCheckedChange={(checked) =>
                updatePreferences({ weekly_report: checked })
              }
            />
          </div>
        </CardContent>
      </Card>

      {/* Preferences */}
      <Card className="border-zinc-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5" />
            Préférences
          </CardTitle>
          <CardDescription>
            Personnalisez votre expérience
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <label className="text-sm font-medium">Mode sombre</label>
              <p className="text-xs text-zinc-500">
                Activez le thème sombre pour l'interface
              </p>
            </div>
            <Switch
              checked={preferences.dark_mode}
              onCheckedChange={(checked) =>
                updatePreferences({ dark_mode: checked })
              }
            />
          </div>
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <label className="text-sm font-medium">Sauvegarde automatique</label>
              <p className="text-xs text-zinc-500">
                Sauvegardez automatiquement vos analyses
              </p>
            </div>
            <Switch
              checked={preferences.auto_save}
              onCheckedChange={(checked) =>
                updatePreferences({ auto_save: checked })
              }
            />
          </div>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button onClick={handleSave} className="gap-2" disabled={isSaving}>
          {isSaving ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Enregistrement...
            </>
          ) : (
            <>
              <Save className="w-4 h-4" />
              Enregistrer les modifications
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
