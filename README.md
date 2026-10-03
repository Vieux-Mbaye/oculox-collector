# Oculox Collector / Hedgehog

Ce depot deploie un Collecteur Oculox. Il conserve sans modification les
services et choix du profil `hedgehog` du depot Gitea : capture PCAP, Zeek,
Suricata, Arkime, Strelka, Filescan, Filebeat, pcap-monitor et services live.

## 1. Prerequis

- VM Debian/Ubuntu avec compte `sudo` ;
- heure synchronisee avec Core et Cluster ;
- interface SPAN/TAP visible par `ip -br link` ;
- sortie TCP vers Core `5044` et `5045` ;
- sortie HTTPS vers Cluster `9200` si Arkime/pcap-monitor ecrivent directement ;
- un bundle Beats unique cree sur le Core ;
- le bundle OpenSearch `hedgehog` cree sur le Cluster.

## 2. Cloner Le Depot Collecteur

```bash
git clone <URL_DEPOT_OCULOX_COLLECTOR> ~/oculox-collector
cd ~/oculox-collector
git status --short
```

La derniere commande ne doit rien afficher. Utilisez la meme version ou le meme
tag Oculox sur les trois VM.

## 3. Creer Les Bundles

Sur le Core :

```bash
./oculox collector-bundle <NOM_COLLECTEUR> <IP_CORE_OU_DNS> \
  ~/oculox-bundles/<NOM_COLLECTEUR>
```

Sur le Cluster :

```bash
./oculox cluster client-bundle hedgehog ~/oculox-bundles/hedgehog
```

Copier les deux repertoires sur la VM Collecteur par SCP, puis verifier :

```bash
(cd ~/oculox-bundles/<NOM_COLLECTEUR> && sha256sum -c SHA256SUMS)
(cd ~/oculox-bundles/hedgehog && sha256sum -c SHA256SUMS)
```

Chaque collecteur doit avoir son propre certificat Beats. Ne reutilisez pas le
meme bundle entre plusieurs capteurs.

## 4. Installer Sans Changer La Procedure

```bash
cd ~/oculox-collector
./oculox install hedgehog \
  --principal-host <IP_CORE_OU_DNS> \
  --collector-name <NOM_COLLECTEUR> \
  --bundle ~/oculox-bundles/<NOM_COLLECTEUR> \
  --opensearch-bundle ~/oculox-bundles/hedgehog
```

Arguments :

| Argument | Signification |
|---|---|
| `install hedgehog` | selectionne le profil Collecteur existant |
| `--principal-host` | Core qui ecoute Filebeat sur `5044/5045` |
| `--collector-name` | identite unique et stable du capteur |
| `--bundle` | CA et certificat mTLS Beats propres au capteur |
| `--opensearch-bundle` | CA et comptes OpenSearch limites au role Hedgehog |

## 5. Choix Dans L'installateur Malcolm

| Ecran | Valeur attendue |
|---|---|
| Profil | `hedgehog` |
| Stockage principal | `opensearch-remote` |
| URL OpenSearch | `https://<IP_CLUSTER>:9200` |
| Verification TLS | `Yes` |
| Capture live | `Yes` pour un capteur raccorde a un miroir |
| Interface de capture | nom exact retourne par `ip -br link` |
| Zeek | `Yes` |
| Suricata | `Yes` |
| Arkime live | `Yes` si requis par l'architecture |
| Hote Logstash | ne pas remplacer les deux destinations fournies par le bundle |

Ne desactivez et ne supprimez aucun service dans Compose. Les choix de capture
se font dans l'assistant officiel, exactement comme dans le depot fusionne.

### `auth_setup` Du Collecteur

Choisir `all`. Le profil Hedgehog n'affiche pas les questions Core relatives a
la methode Basic, au compte administrateur ou au certificat HTTPS Web. Repondre
aux questions affichees comme suit :

| Question | Reponse recommandee | Explication |
|---|---|---|
| Store username/password for OpenSearch | `No` | le bundle `hedgehog` contient deja les comptes limites |
| Generate internal Valkey password | `Yes` | cree un secret local unique |
| Arkime viewer cluster secret | `Yes` | cree le secret local Arkime |
| Receive client certificates from Malcolm | `No` | le bundle Beats du Core a deja ete importe |

Ne pas utiliser le transfert `croc`, puisque les bundles ont deja ete copies,
et ne saisir aucun mot de passe sur la ligne de commande. Si votre ecran affiche
une question supplementaire issue d'un mode optionnel choisi dans l'installateur,
conserver la valeur deja fournie par les bundles plutot que de creer un compte
administrateur partage.

Si le groupe Docker vient d'etre attribue et que la reprise automatique echoue :

```bash
./oculox resume-install hedgehog \
  --principal-host <IP_CORE_OU_DNS> \
  --collector-name <NOM_COLLECTEUR> \
  --bundle ~/oculox-bundles/<NOM_COLLECTEUR> \
  --opensearch-bundle ~/oculox-bundles/hedgehog
```

## 6. Verifier Le Collecteur

```bash
./oculox status
./oculox validate
./oculox logs filebeat
grep -R -nE 'hosts:|loadbalance:|verification_mode:' dev/generated/filebeat
```

Resultat attendu :

- services du profil Hedgehog en cours d'execution ;
- destinations `<CORE>:5044` et `<CORE>:5045` ;
- `loadbalance: true` ;
- `verification_mode: full` ;
- connexions Filebeat etablies sans erreur TLS.

## 7. Test De Bout En Bout

Sur le Core :

```bash
mkdir -p dev/generated/validation/recette
./oculox verify ingestion baseline \
  --output dev/generated/validation/recette/baseline.json
```

Sur le Collecteur :

```bash
./oculox verify ingestion inject \
  --pcap /chemin/vers/test.pcap \
  --run-id recette-01 \
  --output dev/generated/validation/recette/collector.json
```

Copier le rapport Collecteur sur le Core, puis :

```bash
./oculox verify ingestion finalize \
  --baseline dev/generated/validation/recette/baseline.json \
  --collector-report dev/generated/validation/recette/collector.json \
  --output dev/generated/validation/recette/final.json
```

Le resultat attendu est `INGESTION_RESULT=PASS`.

## 8. Exploitation

```bash
./oculox start
./oculox restart [service...]
./oculox status
./oculox logs [service...]
./oculox pull
./oculox validate
./oculox stop
```

`stop` conserve les volumes et les registres Filebeat. Ne jamais utiliser
`docker compose down -v` pendant l'exploitation normale.

Documentation complementaire :

- `dev/docs/13_installation_resiliente_principal_hedgehog.md` ;
- `dev/docs/Opensearch/guide_installation_vm_neuves.md` ;
- `docs/UPSTREAM_README.md`.
