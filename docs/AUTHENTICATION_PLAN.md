# Plan d'implémentation OAuth HubSpot - FilialeAgents

## 📋 Vue d'ensemble

Ce document décrit le plan complet d'implémentation de l'authentification OAuth HubSpot avec un système multi-tenant pour l'application FilialeAgents.

### Objectifs
- ✅ Authentification via OAuth HubSpot
- ✅ Gestion des tokens (access & refresh)
- ✅ Système multi-tenant (Organizations + Users)
- ✅ Rôles utilisateurs (Admin / Member)
- ✅ Persistance des données de recherche par organisation
- ✅ Synchronisation avec HubSpot (Company & Contact data)

---

## 🏗️ Architecture

### Stack technique

| Composant | Technologie | Version |
|-----------|-------------|---------|
| Frontend | Next.js | 15.5.4 |
| Backend | FastAPI | 0.116.2 |
| Base de données | PostgreSQL | 15+ |
| ORM | SQLAlchemy | 2.0+ (async) |
| Migrations | Alembic | 1.13+ |
| Cache/Sessions | Redis | 7+ |
| Authentification | OAuth 2.0 | HubSpot |
| Tokens | JWT | python-jose |

---

## 🗄️ Modèle de données

### Schéma de base de données

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────────┐
│  Organization   │◄────────│      User        │────────►│    OAuthToken       │
│                 │  1    * │                  │  1    1 │                     │
│ - id            │         │ - id             │         │ - id                │
│ - hubspot_id    │         │ - organization_id│         │ - user_id           │
│ - name          │         │ - hubspot_user_id│         │ - access_token (enc)│
│ - domain        │         │ - email          │         │ - refresh_token(enc)│
│ - plan          │         │ - role           │         │ - expires_at        │
│ - is_active     │         │ - is_active      │         │ - scope             │
└─────────────────┘         └──────────────────┘         └─────────────────────┘
         │                           │
         │ 1                         │ 1
         │                           │
         │ *                         │ *
         │                           │
         ▼                           ▼
┌─────────────────────────────────────────────────┐
│           CompanyExtraction                     │
│                                                 │
│ - id                                            │
│ - organization_id (FK)                          │
│ - user_id (FK)                                  │
│ - session_id                                    │
│ - company_name                                  │
│ - company_url                                   │
│ - extraction_data (JSONB)                       │
│ - status (pending/running/completed/failed)     │
│ - subsidiaries_count                            │
│ - created_at / updated_at / completed_at        │
└─────────────────────────────────────────────────┘
```

### Tables

#### 1. **Organization**
Entreprise cliente (synchronisée avec HubSpot Company)

```python
- id: UUID (PK)
- hubspot_company_id: String (unique, indexed)
- name: String
- domain: String
- plan_type: Enum (free, starter, professional, enterprise)
- max_searches_per_month: Integer
- is_active: Boolean
- settings: JSONB
- created_at, updated_at: DateTime
```

#### 2. **User**
Utilisateur (synchronisé avec HubSpot Contact/User)

```python
- id: UUID (PK)
- organization_id: UUID (FK → Organization)
- hubspot_user_id: String (unique, indexed)
- email: String (unique, indexed)
- first_name, last_name: String
- role: Enum (admin, member)
- is_active: Boolean
- last_login_at: DateTime
- created_at, updated_at: DateTime
```

#### 3. **OAuthToken**
Tokens OAuth HubSpot (chiffrés)

```python
- id: UUID (PK)
- user_id: UUID (FK → User, unique)
- access_token: Text (encrypted)
- refresh_token: Text (encrypted)
- token_type: String
- expires_at: DateTime
- scope: String
- created_at, updated_at: DateTime
```

#### 4. **CompanyExtraction**
Historique des recherches d'entreprises

```python
- id: UUID (PK)
- organization_id: UUID (FK → Organization)
- user_id: UUID (FK → User)
- session_id: String (unique, indexed)
- company_name: String
- company_url: String
- extraction_type: Enum (name, url)
- extraction_data: JSONB (résultats complets)
- status: Enum (pending, running, completed, failed)
- error_message: Text
- processing_time: Float
- subsidiaries_count: Integer
- created_at, updated_at, completed_at: DateTime
```

#### 5. **OrganizationUsage**
Statistiques d'utilisation mensuelle

```python
- id: UUID (PK)
- organization_id: UUID (FK → Organization)
- month: DateTime (first day of month)
- searches_count: Integer
- api_calls_count: Integer
- created_at, updated_at: DateTime
- UNIQUE(organization_id, month)
```

### Rôles utilisateurs

```python
class UserRole(Enum):
    ADMIN = "admin"    # Admin du compte HubSpot
    MEMBER = "member"  # Utilisateur standard
```

### Permissions

| Action | Admin | Member |
|--------|-------|--------|
| Créer extraction | ✅ | ✅ |
| Voir extractions de l'org | ✅ | ✅ |
| Supprimer ses propres extractions | ✅ | ✅ |
| Supprimer toutes les extractions | ✅ | ❌ |
| Gérer les utilisateurs | ✅ | ❌ |
| Gérer le plan/settings | ✅ | ❌ |

---

## 🔐 Flux d'authentification OAuth

### 1. Connexion initiale

```mermaid
sequenceDiagram
    User->>Frontend: Clique "Se connecter avec HubSpot"
    Frontend->>Backend: GET /auth/hubspot/login
    Backend->>Backend: Génère state (CSRF protection)
    Backend->>Frontend: Redirect URL HubSpot
    Frontend->>HubSpot: Redirect vers OAuth
    HubSpot->>User: Page de consentement
    User->>HubSpot: Accepte
    HubSpot->>Backend: Redirect /auth/hubspot/callback?code=XXX
    Backend->>HubSpot: Exchange code pour tokens
    HubSpot->>Backend: access_token + refresh_token
    Backend->>HubSpot API: GET user info
    Backend->>HubSpot API: GET company info
    Backend->>Database: Créer/MAJ Organization
    Backend->>Database: Créer/MAJ User
    Backend->>Database: Stocker tokens (encrypted)
    Backend->>Backend: Génère JWT (access + refresh)
    Backend->>Frontend: Redirect avec JWT
    Frontend->>Frontend: Stocke tokens
    Frontend->>User: Connecté ✅
```

### 2. Requêtes authentifiées

```mermaid
sequenceDiagram
    Frontend->>Backend: API Request + JWT Bearer Token
    Backend->>Backend: Vérifie JWT signature
    Backend->>Backend: Extrait user_id du JWT
    Backend->>Database: Charge User + Organization
    Backend->>Backend: Vérifie permissions
    Backend->>Backend: Exécute requête
    Backend->>Frontend: Response
```

### 3. Refresh de token

```mermaid
sequenceDiagram
    Frontend->>Backend: POST /auth/refresh (refresh_token)
    Backend->>Backend: Vérifie refresh token
    Backend->>Database: Charge User
    Backend->>Backend: Génère nouveau access_token
    Backend->>Frontend: Nouveau JWT access_token
```

---

## 📦 Plan d'implémentation par phases

### ✅ **Phase 1 : Configuration & Préparation** [TERMINÉE]

#### 1.1. Configuration HubSpot [MANUEL]
- [ ] Créer application sur https://developers.hubspot.com/
- [ ] Récupérer CLIENT_ID et CLIENT_SECRET
- [ ] Configurer Redirect URI: `http://localhost:8012/auth/hubspot/callback`
- [ ] Définir les scopes: `oauth`, `crm.objects.contacts.read`, `crm.objects.companies.read`

#### 1.2. Infrastructure ✅
- ✅ Ajout PostgreSQL au docker-compose.yml
- ✅ Configuration volumes et healthchecks
- ✅ Variables d'environnement DATABASE_URL

#### 1.3. Dépendances ✅
- ✅ `python-jose[cryptography]` - JWT
- ✅ `passlib[bcrypt]` - Hashing
- ✅ `sqlalchemy[asyncio]` - ORM async
- ✅ `alembic` - Migrations
- ✅ `asyncpg` - Driver PostgreSQL async
- ✅ `psycopg2-binary` - Driver PostgreSQL sync

#### 1.4. Modèles de données ✅
- ✅ Création `api/models/db_models.py` (SQLAlchemy)
- ✅ Création `api/models/auth.py` (Pydantic schemas)
- ✅ Création `api/core/database.py` (Configuration DB)
- ✅ Modèles: Organization, User, OAuthToken, CompanyExtraction, OrganizationUsage

#### 1.5. Configuration ✅
- ✅ Extension `api/core/config.py` (DATABASE_URL, HUBSPOT_*, JWT_*)
- ✅ Mise à jour `.env.example`

#### 1.6. Migrations ✅
- ✅ Initialisation Alembic (`api/alembic/`)
- ✅ Configuration `env.py` pour async
- ✅ Migration initiale `001_initial_schema.py`

**Fichiers créés (Phase 1):**
```
api/
├── alembic/
│   ├── versions/
│   │   └── 001_initial_schema.py
│   ├── env.py
│   └── script.py.mako
├── alembic.ini
├── models/
│   ├── __init__.py
│   ├── auth.py
│   └── db_models.py
└── core/
    ├── config.py (modifié)
    └── database.py (nouveau)
```

---

### 🔄 **Phase 2 : Backend - Routes OAuth** [À FAIRE]

#### 2.1. Service d'authentification
Fichier: `api/services/auth_service.py`

**Responsabilités:**
- Gestion du flow OAuth HubSpot
- Exchange code → tokens
- Récupération des infos utilisateur via HubSpot API
- Récupération des infos company via HubSpot API
- Création/mise à jour Organization
- Création/mise à jour User
- Détection du rôle (Admin = super admin HubSpot ou premier user)
- Stockage des tokens OAuth (chiffrés)
- Refresh des tokens OAuth expirés
- Génération de JWT (access + refresh)

**Fonctions principales:**
```python
async def get_hubspot_authorization_url(state: str) -> str
async def exchange_code_for_tokens(code: str) -> OAuthTokenResponse
async def get_hubspot_user_info(access_token: str) -> HubSpotUserInfo
async def get_hubspot_company_info(access_token: str, hub_id: int) -> HubSpotCompanyInfo
async def create_or_update_organization(company_info: HubSpotCompanyInfo) -> Organization
async def create_or_update_user(user_info: HubSpotUserInfo, org: Organization) -> User
async def determine_user_role(user_info: HubSpotUserInfo, org: Organization) -> UserRole
async def store_oauth_tokens(user: User, tokens: OAuthTokenResponse) -> OAuthToken
async def refresh_oauth_token(user: User) -> OAuthToken
async def encrypt_token(token: str) -> str
async def decrypt_token(encrypted_token: str) -> str
```

#### 2.2. Service JWT
Fichier: `api/services/jwt_service.py`

**Responsabilités:**
- Génération de JWT access tokens
- Génération de JWT refresh tokens
- Validation et vérification des tokens
- Extraction des données du payload

**Fonctions principales:**
```python
def create_access_token(data: dict, expires_delta: timedelta) -> str
def create_refresh_token(data: dict) -> str
def verify_token(token: str) -> TokenData
def decode_token(token: str) -> dict
```

#### 2.3. Router d'authentification
Fichier: `api/routers/auth.py`

**Endpoints:**
```python
GET  /auth/hubspot/login
     → Initie le flow OAuth
     → Génère state pour CSRF protection
     → Retourne redirect_url vers HubSpot

GET  /auth/hubspot/callback
     → Reçoit code et state de HubSpot
     → Vérifie state (CSRF)
     → Exchange code pour tokens
     → Récupère user et company info
     → Crée/MAJ Organization et User
     → Génère JWT
     → Retourne tokens + user info

POST /auth/refresh
     → Body: {refresh_token: string}
     → Vérifie refresh token
     → Génère nouveau access token
     → Retourne nouveau JWT

POST /auth/logout
     → Invalide les tokens (optionnel: blacklist Redis)
     → Retourne success

GET  /auth/me
     → Retourne infos utilisateur courant
     → Requires: JWT Bearer token
```

---

### 🔒 **Phase 3 : Backend - Sécurité** [À FAIRE]

#### 3.1. Dépendances FastAPI
Fichier: `api/dependencies/auth.py`

**Fonctions:**
```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User
    → Extrait JWT du header Authorization
    → Vérifie et décode le token
    → Charge l'utilisateur depuis la DB
    → Retourne User ou raise 401

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User
    → Vérifie que user.is_active = True
    → Retourne User ou raise 403

async def require_admin(
    current_user: User = Depends(get_current_active_user)
) -> User
    → Vérifie que user.role = ADMIN
    → Retourne User ou raise 403

async def get_current_organization(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Organization
    → Charge l'organisation de l'utilisateur
    → Vérifie que org.is_active = True
    → Retourne Organization ou raise 403
```

#### 3.2. Middleware d'authentification
Fichier: `api/middleware/auth.py`

**Optionnel:** Middleware global pour logger les requêtes authentifiées

#### 3.3. Sécurisation des routes existantes
Modifier les routers existants:
- `api/routers/extraction.py`
- `api/routers/websocket.py`

**Exemple:**
```python
@router.post("/extract")
async def extract_company(
    request: CompanyExtractionRequest,
    current_user: User = Depends(get_current_active_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    # Vérifier les limites du plan
    usage = await get_current_month_usage(organization.id, db)
    if usage.searches_count >= organization.max_searches_per_month:
        raise HTTPException(403, "Monthly search limit reached")

    # Créer l'extraction
    extraction = CompanyExtraction(
        organization_id=organization.id,
        user_id=current_user.id,
        company_name=request.company_name,
        ...
    )

    # Incrémenter le compteur
    await increment_usage(organization.id, db)

    # Lancer l'extraction
    ...
```

---

### 🎨 **Phase 4 : Frontend - UI d'authentification** [À FAIRE]

#### 4.1. Page de login
Fichier: `frontend/src/app/login/page.tsx`

**Composants:**
- Bouton "Se connecter avec HubSpot"
- Gestion des erreurs d'authentification
- Loading states
- Redirection après connexion

#### 4.2. Page de callback OAuth
Fichier: `frontend/src/app/auth/callback/page.tsx`

**Logique:**
- Récupère les query params (code, state, error)
- Affiche un loader pendant le traitement
- Gère les erreurs
- Redirige vers le dashboard après succès

#### 4.3. Context d'authentification
Fichier: `frontend/src/contexts/AuthContext.tsx`

**État global:**
```typescript
interface AuthState {
  user: User | null
  organization: Organization | null
  isAuthenticated: boolean
  isLoading: boolean
  login: () => void
  logout: () => void
  refreshToken: () => Promise<void>
}
```

#### 4.4. Hook d'authentification
Fichier: `frontend/src/hooks/use-auth.ts`

**Fonctionnalités:**
- Stockage des tokens (localStorage ou httpOnly cookies)
- Auto-refresh des tokens avant expiration
- Vérification de l'état de connexion
- Logout avec nettoyage

```typescript
export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Auto-refresh token avant expiration
  useEffect(() => {
    const interval = setInterval(async () => {
      await refreshAccessToken()
    }, 10 * 60 * 1000) // Toutes les 10 minutes

    return () => clearInterval(interval)
  }, [])

  // ...
}
```

#### 4.5. Composant de protection des routes
Fichier: `frontend/src/components/auth/ProtectedRoute.tsx`

```typescript
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, isLoading])

  if (isLoading) return <LoadingSpinner />
  if (!isAuthenticated) return null

  return <>{children}</>
}
```

#### 4.6. Bouton de login
Fichier: `frontend/src/components/auth/LoginButton.tsx`

```typescript
export function LoginButton() {
  const handleLogin = () => {
    window.location.href = `${API_URL}/auth/hubspot/login`
  }

  return (
    <button onClick={handleLogin}>
      <HubSpotIcon />
      Se connecter avec HubSpot
    </button>
  )
}
```

---

### 🔗 **Phase 5 : Frontend - Intégration** [À FAIRE]

#### 5.1. Modification du layout principal
Fichier: `frontend/src/app/layout.tsx`

**Ajouts:**
- Wrapper avec AuthProvider
- Navbar avec statut de connexion
- Menu utilisateur avec logout

#### 5.2. Intercepteur Axios
Fichier: `frontend/src/lib/api.ts`

**Fonctionnalités:**
```typescript
// Request interceptor
axiosInstance.interceptors.request.use(
  (config) => {
    const token = getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  }
)

// Response interceptor
axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Token expiré, tenter refresh
      const refreshed = await refreshAccessToken()
      if (refreshed) {
        // Retry la requête originale
        return axiosInstance.request(error.config)
      } else {
        // Redirect vers login
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)
```

#### 5.3. Protection des pages
Wrapper les pages existantes avec `ProtectedRoute`:
- `frontend/src/app/page.tsx`
- `frontend/src/app/results/[id]/page.tsx`
- Toutes les pages nécessitant l'authentification

#### 5.4. Menu utilisateur
Fichier: `frontend/src/components/navigation/UserMenu.tsx`

**Contenu:**
- Avatar / Email
- Nom de l'organisation
- Plan actuel
- Lien vers settings (si admin)
- Bouton logout

#### 5.5. Dashboard organisation (optionnel)
Fichier: `frontend/src/app/dashboard/page.tsx`

**Sections:**
- Statistiques d'utilisation
- Liste des recherches récentes
- Membres de l'équipe (si admin)
- Limites du plan

---

### ⚙️ **Phase 6 : Configuration & Tests** [À FAIRE]

#### 6.1. Variables d'environnement

**Backend (.env):**
```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/filialeagents

# HubSpot OAuth
HUBSPOT_CLIENT_ID=xxx
HUBSPOT_CLIENT_SECRET=xxx
HUBSPOT_REDIRECT_URI=http://localhost:8012/auth/hubspot/callback

# JWT
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

**Frontend (.env.local):**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8012
NEXT_PUBLIC_WS_URL=ws://localhost:8012
```

#### 6.2. Lancement des services

```bash
# 1. Lancer les services Docker
docker-compose up postgres redis -d

# 2. Appliquer les migrations
cd api
uv run python3 -c "from alembic.config import Config; from alembic import command; cfg = Config('alembic.ini'); command.upgrade(cfg, 'head')"

# 3. Lancer le backend
cd api
uv run uvicorn main:app --reload --port 8012

# 4. Lancer le frontend
cd frontend
npm run dev
```

#### 6.3. Tests à effectuer

**Tests manuels:**
1. Flow OAuth complet (login → callback → JWT)
2. Création automatique Organization + User
3. Détection du rôle Admin/Member
4. Refresh de token
5. Logout
6. Protection des routes
7. Requêtes authentifiées
8. Limites de plan (quota mensuel)
9. Persistance des extractions
10. Multi-tenant isolation

**Tests d'intégration:**
- Connexion avec 2 utilisateurs différents
- Vérifier l'isolation des données par org
- Tester les permissions Admin vs Member
- Vérifier le refresh automatique des tokens

#### 6.4. Documentation Swagger

Tester tous les endpoints dans `/docs`:
- `GET /auth/hubspot/login`
- `GET /auth/hubspot/callback`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /auth/me`
- `POST /extract` (avec auth)

---

## 🔐 Sécurité

### Bonnes pratiques implémentées

1. **Tokens OAuth chiffrés** en base de données
2. **JWT avec expiration courte** (15 min access, 7 jours refresh)
3. **State parameter** pour protection CSRF dans OAuth
4. **HTTPS obligatoire** en production
5. **CORS restreints** en production (pas `["*"]`)
6. **httpOnly cookies** pour refresh tokens (recommandé)
7. **Rate limiting** sur les endpoints d'auth (à ajouter)
8. **Validation stricte** des inputs avec Pydantic
9. **Secrets en variables d'environnement**

### À améliorer en production

- [ ] Implémenter rate limiting (SlowAPI ou middleware custom)
- [ ] Ajouter token blacklist dans Redis pour logout
- [ ] Logs d'audit pour actions sensibles
- [ ] Monitoring des tentatives de connexion échouées
- [ ] Rotation automatique des JWT secrets
- [ ] 2FA optionnel (via HubSpot si supporté)

---

## 📊 Métriques et monitoring

### Événements à tracker

1. **Authentification:**
   - Connexions réussies/échouées
   - Refresh de tokens
   - Logouts

2. **Utilisation:**
   - Nombre de recherches par org/mois
   - Temps de traitement moyen
   - Taux de succès/échec des extractions

3. **Erreurs:**
   - Erreurs OAuth
   - Tokens expirés
   - Limites de plan atteintes

---

## 📚 Ressources

### Documentation HubSpot
- OAuth 2.0: https://developers.hubspot.com/docs/api/oauth/overview
- API Reference: https://developers.hubspot.com/docs/api/overview
- Scopes: https://developers.hubspot.com/docs/api/oauth/scopes

### Documentation technique
- FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/
- SQLAlchemy Async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- Alembic: https://alembic.sqlalchemy.org/
- python-jose: https://python-jose.readthedocs.io/

---

## 🎯 Prochaines étapes

1. ✅ **Phase 1 complétée** - Infrastructure et modèles de données
2. 🔄 **Phase 2** - Implémenter les routes OAuth backend
3. 🔄 **Phase 3** - Sécuriser les endpoints existants
4. 🔄 **Phase 4** - Créer l'UI d'authentification frontend
5. 🔄 **Phase 5** - Intégrer l'auth dans toute l'application
6. 🔄 **Phase 6** - Tests et déploiement

---

## 📝 Notes d'implémentation

### Décisions techniques

1. **PostgreSQL vs NoSQL**: PostgreSQL choisi pour relations complexes et transactions ACID
2. **SQLAlchemy async**: Pour performance avec FastAPI async
3. **JWT vs Sessions**: JWT pour stateless API et scalabilité
4. **Rôles simplifiés**: Admin/Member uniquement (pas de viewer)
5. **Tokens chiffrés**: Sécurité des tokens OAuth au repos
6. **JSONB pour extraction_data**: Flexibilité des résultats

### Limitations connues

1. **Pas de SSO natif**: Dépend de l'auth HubSpot
2. **Pas de MFA intégré**: Dépend de HubSpot
3. **Synchronisation manuelle**: Pas de webhooks HubSpot (pour l'instant)
4. **Limites de plan statiques**: Pas de billing automatique

---

**Document créé le:** 2025-01-24
**Dernière mise à jour:** 2025-01-24
**Version:** 1.0
**Statut:** Phase 1 complétée ✅
