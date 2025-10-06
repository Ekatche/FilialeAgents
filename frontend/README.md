# 🚀 Company Analyzer - Frontend

Une plateforme web moderne développée en Next.js pour l'analyse intelligente d'entreprises utilisant l'IA.

## ✨ Fonctionnalités

- **Interface moderne** : Design responsive avec Tailwind CSS et animations Framer Motion
- **Recherche intelligente** : Recherche par nom d'entreprise ou URL de site web
- **Visualisation avancée** : Graphiques interactifs et tableaux de bord analytiques
- **Export de données** : Export des analyses au format JSON
- **Partage social** : Partage des résultats d'analyse
- **Temps réel** : Intégration avec l'API FastAPI existante
- **Optimisations** : Cache intelligent et gestion d'erreur robuste

## 🛠️ Technologies

- **Framework** : Next.js 14 (App Router)
- **Styling** : Tailwind CSS + CSS personnalisé
- **Animations** : Framer Motion
- **Charts** : Recharts
- **Icons** : Lucide React + Heroicons
- **HTTP Client** : Axios + SWR
- **Notifications** : React Hot Toast
- **TypeScript** : Support complet

## 🚀 Installation et Démarrage

### Prérequis

- Node.js 18+
- npm ou yarn
- L'API FastAPI doit être démarrée sur le port 8000

### Installation

```bash
# Installer les dépendances
npm install

# Copier le fichier d'environnement
cp .env.example .env.local

# Démarrer le serveur de développement
npm run dev
```

L'application sera disponible sur : `http://localhost:3000`

### Configuration

Créez un fichier `.env.local` avec :

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 📁 Structure du Projet

```
frontend/
├── src/
│   ├── app/                    # App Router (Next.js 13+)
│   │   ├── globals.css        # Styles globaux
│   │   ├── layout.tsx         # Layout principal
│   │   └── page.tsx           # Page d'accueil
│   ├── components/            # Composants réutilisables
│   │   ├── ui/               # Composants UI de base
│   │   ├── company/          # Composants spécifiques aux entreprises
│   │   ├── dashboard/        # Composants de tableau de bord
│   │   └── analytics/        # Composants d'analyse
│   └── lib/                  # Utilitaires et configuration
│       ├── api.ts           # Client API
│       └── utils.ts         # Fonctions utilitaires
├── public/                   # Assets statiques
└── tailwind.config.ts       # Configuration Tailwind
```

## 🎨 Composants Principaux

### CompanyDashboard

Le composant principal qui orchestre toute l'application :

- Gestion de l'état global
- Recherche d'entreprises
- Affichage des résultats
- Gestion des erreurs

### CompanySearch

Interface de recherche avec :

- Recherche par nom d'entreprise
- Recherche par URL
- Auto-détection du type de recherche
- Historique de recherche

### CompanyOverview

Vue d'ensemble de l'entreprise :

- Informations générales
- Métriques clés
- Siège social
- Structure organisationnelle

### SubsidiariesList

Liste interactive des filiales :

- Cartes expansibles
- Informations détaillées
- Statistiques de répartition
- Gestion des états de confiance

### CompanyAnalytics

Visualisations avancées :

- Distribution géographique
- Activités commerciales
- Scores de confiance
- Types de filiales

## 🔌 Intégration API

L'application s'intègre avec l'API FastAPI existante via :

- **GET /health** : Vérification de l'état de l'API
- **POST /extract** : Extraction par nom d'entreprise
- **POST /extract-from-url** : Extraction par URL
- **GET /extract/{company_name}** : Extraction simple par nom

## 🎯 Fonctionnalités Avancées

### Gestion des États

- États de chargement avec spinners animés
- Gestion d'erreur avec messages contextuels
- États vides avec invitations à l'action

### Optimisations Performance

- Lazy loading des composants
- Debouncing des recherches
- Cache des requêtes API
- Optimisation des re-renders

### Accessibilité

- Support clavier complet
- ARIA labels appropriés
- Contrastes respectant WCAG
- Navigation au clavier

### Responsive Design

- Mobile-first approach
- Breakpoints adaptatifs
- Touch-friendly sur mobile
- Optimisation tablette

## 🚀 Déploiement

### Build de Production

```bash
npm run build
npm start
```

### Docker (Optionnel)

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

### Variables d'Environnement de Production

```env
NEXT_PUBLIC_API_URL=https://your-api-domain.com
NODE_ENV=production
```

## 🧪 Tests et Qualité

### Linting

```bash
npm run lint
npm run lint:fix
```

### Build Check

```bash
npm run build
```

## 📈 Métriques et Analytics

L'application suit :

- Temps de réponse API
- Taux de succès des recherches
- Types de recherches populaires
- Erreurs utilisateur

## 🔧 Personnalisation

### Thème et Couleurs

Modifiez `tailwind.config.ts` pour personnaliser :

- Palette de couleurs
- Typographie
- Espacements
- Animations

### Composants UI

Les composants dans `src/components/ui/` sont facilement personnalisables et réutilisables.

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add AmazingFeature'`)
4. Push sur la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 📝 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 🆘 Support

Pour toute question ou problème :

- Ouvrir une issue sur GitHub
- Consulter la documentation de l'API
- Vérifier les logs de développement

---

Développé avec ❤️ pour l'analyse intelligente d'entreprises
