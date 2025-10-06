# 🏢 Company Information Extraction API

API FastAPI pour extraire les informations d'entreprise et leurs filiales en utilisant OpenAI Agents.

> **Note** : Ce dossier contient l'API de production. Les notebooks d'expérimentation sont dans le dossier parent.

## 🚀 Fonctionnalités

- **Extraction intelligente** : Détecte automatiquement si une entreprise est une filiale ou une entreprise principale
- **Stratégie optimisée** : Remonte à l'entreprise mère et extrait toutes les filiales liées
- **API asynchrone** : Utilise FastAPI pour des performances optimales
- **Minimisation des requêtes** : Optimisé pour réduire les coûts API OpenAI
- **Support URL** : Peut extraire le nom d'entreprise depuis une URL
- **Documentation automatique** : Swagger UI intégré

## 📋 Prérequis

- Python 3.8+
- Clé API OpenAI
- OpenAI Agents (selon la documentation fournie)

## 🛠️ Installation

1. **Cloner le projet** :

```bash
git clone <votre-repo>
cd OpenAiAgents/api
```

2. **Installer les dépendances** :

```bash
pip install -r requirements.txt
```

3. **Configurer la clé API** :

```bash
export OPENAI_API_KEY="votre-cle-api-openai"
```

Ou créer un fichier `.env` :

```env
OPENAI_API_KEY=votre-cle-api-openai
```

## 🚀 Utilisation

### Démarrage de l'API

```bash
python main.py
```

L'API sera disponible sur : `http://localhost:8000`

### Documentation interactive

- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc

## 📡 Endpoints

### 1. Extraction par nom d'entreprise (POST)

```bash
curl -X POST "http://localhost:8000/extract" \
     -H "Content-Type: application/json" \
     -d '{
       "company_name": "Apple Inc.",
       "include_subsidiaries": true,
       "max_subsidiaries": 50
     }'
```

### 2. Extraction par nom d'entreprise (GET)

```bash
curl "http://localhost:8000/extract/Apple%20Inc."
```

### 3. Extraction depuis une URL

```bash
curl -X POST "http://localhost:8000/extract-from-url" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.apple.com"}'
```

### 4. Vérification de santé

```bash
curl "http://localhost:8000/health"
```

## 📊 Structure de la réponse

```json
{
  "company_name": "Apple Inc.",
  "headquarters_address": "1 Apple Park Way",
  "headquarters_city": "Cupertino",
  "headquarters_country": "United States",
  "parent_company": null,
  "subsidiaries": ["Apple Europe Limited", "Apple Japan Inc."],
  "subsidiaries_details": [
    {
      "subsidiary_name": "Apple Europe Limited",
      "subsidiary_address": "1 Hanover Street, London W1S 1YZ",
      "subsidiary_city": "London",
      "subsidiary_country": "United Kingdom",
      "subsidiary_type": "Regional Headquarters",
      "business_activity": "Sales and Marketing for Europe",
      "employee_count": "5000",
      "establishment_date": "1980",
      "parent_company": "Apple Inc.",
      "confidence_score": 0.9,
      "sources": ["Apple Annual Report", "Companies House UK"]
    }
  ],
  "core_business": "Technology and Consumer Electronics",
  "industry_sector": "Technology",
  "revenue": "$394.3 billion",
  "employee_count": "164,000",
  "confidence_score": 0.85,
  "sources": ["Apple Annual Report", "SEC Filing"],
  "extraction_date": "2025-01-10T01:30:00",
  "extraction_status": "success",
  "total_subsidiaries": 2,
  "detailed_subsidiaries": 2,
  "optimization_note": "Utilise un seul agent pour minimiser les requêtes API",
  "processing_time_seconds": 15.2
}
```

## 🏗️ Architecture

```
OpenAiAgents/
├── main.py              # API FastAPI principale
├── models.py            # Modèles Pydantic
├── agents.py            # Agents OpenAI
├── functions.py         # Fonctions utilitaires
├── requirements.txt     # Dépendances
├── README.md           # Documentation
└── .env                # Variables d'environnement (optionnel)
```

## 🤖 Agents OpenAI

### 1. Company Analyzer

- Détecte si une entreprise est une filiale ou une entreprise principale
- Identifie l'entreprise mère si applicable

### 2. Information Extractor

- Extrait les informations de base de l'entreprise
- Recherche le siège social, secteur d'activité, données financières

### 3. Subsidiaries Extractor

- Identifie toutes les filiales de l'entreprise
- Extrait les détails de chaque filiale (adresse, type, activité)

### 4. Data Validator

- Valide la cohérence des données extraites
- Calcule les scores de confiance

### 5. Extraction Manager

- Orchestre tous les agents
- Implémente la stratégie intelligente filiale ↔ entreprise principale

## ⚡ Optimisations

- **Minimisation des requêtes** : Utilise un seul agent au lieu de 4
- **Stratégie intelligente** : Détecte automatiquement les relations filiale/entreprise principale
- **Gestion d'erreurs** : Retourne des réponses structurées même en cas d'erreur
- **Logging complet** : Traçabilité de toutes les opérations

## 🔧 Configuration

### Variables d'environnement

```env
OPENAI_API_KEY=votre-cle-api-openai
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000
```

### Configuration de production

```bash
# Avec Gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Avec Docker
docker build -t company-extraction-api .
docker run -p 8000:8000 -e OPENAI_API_KEY=your-key company-extraction-api
```

## 🧪 Tests

```bash
# Tests unitaires
pytest

# Tests avec couverture
pytest --cov=.

# Tests d'intégration
pytest tests/integration/
```

## 📈 Monitoring

- **Logs** : Fichier `company_extraction.log`
- **Métriques** : Temps de traitement, scores de confiance
- **Health check** : Endpoint `/health`

## 🚨 Gestion d'erreurs

L'API gère automatiquement :

- Erreurs de validation des données
- Erreurs de quota OpenAI
- Erreurs de réseau
- Erreurs de parsing

## 🔒 Sécurité

- Validation des entrées
- Limitation des requêtes (à configurer)
- Logs sécurisés (pas de données sensibles)
- CORS configurable

## 📚 Exemples d'utilisation

### Python

```python
import httpx

async def extract_company(company_name):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/extract",
            json={"company_name": company_name}
        )
        return response.json()

# Utilisation
result = await extract_company("Apple Inc.")
print(f"Entreprise: {result['company_name']}")
print(f"Filiales: {len(result['subsidiaries'])}")
```

### JavaScript

```javascript
const extractCompany = async (companyName) => {
  const response = await fetch("http://localhost:8000/extract", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      company_name: companyName,
    }),
  });
  return await response.json();
};

// Utilisation
const result = await extractCompany("Apple Inc.");
console.log(`Entreprise: ${result.company_name}`);
console.log(`Filiales: ${result.subsidiaries.length}`);
```

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 🆘 Support

- **Issues** : [GitHub Issues](https://github.com/votre-repo/issues)
- **Documentation** : http://localhost:8000/docs
- **Email** : support@votre-domaine.com

## 🔄 Changelog

### Version 1.0.0

- ✅ API FastAPI complète
- ✅ Agents OpenAI optimisés
- ✅ Stratégie intelligente filiale ↔ entreprise principale
- ✅ Support URL et nom d'entreprise
- ✅ Documentation automatique
- ✅ Gestion d'erreurs robuste
