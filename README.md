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
- entree TCP `8005` autorisee uniquement depuis le Core si Arkime Live est actif ;
- un bundle Beats unique cree sur le Core ;
- le bundle OpenSearch `hedgehog` cree sur le Cluster.

Fiche a remplir :

| Valeur | Exemple | Regle |
|---|---|---|
| `IP_CORE_OU_DNS` | `192.168.1.103` | meme identite que le Core |
| `IP_CLUSTER` | `192.168.1.250` | endpoint OpenSearch |
| `NOM_COLLECTEUR` | `collector-01` | unique, stable, sans espace |
| `INTERFACE_CAPTURE` | `ens33` | interface SPAN/TAP reelle |
| `IP_COLLECTEUR_OU_DNS` | `192.168.1.20` | adresse du Collecteur joignable depuis le Core |

Verifier `timedatectl status`, `ip -br link`, `ip -s link` et `df -h /`. Une
interface UP sans paquets issus du SPAN/TAP ne produira aucun evenement.

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

L'installation du Cluster cree automatiquement le bundle OpenSearch Hedgehog :

```text
~/oculox-cluster/dev/generated/opensearch-cluster/client-bundles/hedgehog
```

La commande `cluster client-bundle hedgehog` n'est donc pas necessaire dans le
parcours normal. Elle reste disponible pour reexporter le bundle automatique
s'il a ete supprime ou si un autre emplacement de sortie est requis.

Copier le bundle Beats depuis le Core et le bundle `hedgehog` automatique
depuis le Cluster sur la VM Collecteur, puis verifier les deux repertoires :

```bash
mkdir -p ~/oculox-bundles
scp -r <UTILISATEUR_CORE>@<IP_CORE>:~/oculox-bundles/<NOM_COLLECTEUR> ~/oculox-bundles/
scp -r <UTILISATEUR_CLUSTER>@<IP_CLUSTER>:~/oculox-cluster/dev/generated/opensearch-cluster/client-bundles/hedgehog ~/oculox-bundles/
(cd ~/oculox-bundles/<NOM_COLLECTEUR> && sha256sum -c SHA256SUMS)
(cd ~/oculox-bundles/hedgehog && sha256sum -c SHA256SUMS)
```

Chaque collecteur doit avoir son propre certificat Beats. Ne reutilisez pas le
meme bundle entre plusieurs capteurs.

Les bundles contiennent des secrets. Appliquer `chmod -R go-rwx
~/oculox-bundles`, ne jamais les versionner et retirer les copies de transfert
devenues inutiles apres la recette.

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

Le script verifie les checksums, le nom du Collecteur, le Core attendu et la
correspondance certificat/cle. Le bundle contient aussi le secret de cluster
Arkime du Core, sans aucun identifiant humain. Il est importe automatiquement
sur le Collecteur afin que le Viewer du Core puisse recuperer les paquets. Le
nom et le host doivent correspondre exactement aux valeurs utilisees lors de la
creation du bundle Beats.

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
| Arkime Node Host | `<IP_COLLECTEUR_OU_DNS>` joignable depuis le Core |
| Hote Logstash | ne pas remplacer les deux destinations fournies par le bundle |

Pour une capture PCAP standard, activer Arkime live, renseigner `Arkime Node Host`
avec l'IP ou le DNS du Collecteur, conserver `PCAP Compression: none` sauf
politique explicite, et laisser
`netsniff-ng` et `tcpdump` desactives. Plusieurs moteurs PCAP simultanes
dupliquent les captures. Zeek et Suricata peuvent rester actifs en parallele.

Les metadonnees Arkime sont ecrites directement dans OpenSearch, mais les PCAP
restent sur le Collecteur. Quand un operateur ouvre les paquets d'une session,
le Viewer du Core contacte alors `<IP_COLLECTEUR_OU_DNS>:8005`. Arkime Live
utilise le reseau de l'hote ; son Viewer ecoute sur `8005` lorsqu'il est actif.
Restreindre le flux au Core dans le pare-feu de la VM ou l'ACL reseau. Si
l'assistant affiche `Oculox
Reachback ACL`, renseigner uniquement l'IP du Core.

WISE est heberge sur le Core, pas sur le profil Hedgehog. Si une URL WISE
distante est demandee, utiliser `https://<IP_CORE_OU_DNS>/wise/`, sans
identifiants. Si WISE n'est pas souhaite, le desactiver ne doit pas bloquer
l'installation ou Filebeat.

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
| Arkime viewer cluster secret | `No` | le secret commun du Core est importe du bundle apres cet assistant |
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
./oculox verify clients
./oculox verify wise
./oculox logs filebeat
grep -R -nE 'hosts:|loadbalance:|verification_mode:' dev/generated/filebeat
```

Resultat attendu :

- services du profil Hedgehog en cours d'execution ;
- destinations `<CORE>:5044` et `<CORE>:5045` ;
- `loadbalance: true` ;
- `verification_mode: full` ;
- connexions Filebeat etablies sans erreur TLS.
- `CLIENT_CONNECTIVITY_RESULT=PASS`, y compris les negociations mTLS sur `5044` et `5045` et l'ecriture Arkime directe ;
- `WISE_RUNTIME=PASS` si une URL WISE distante est configuree, ou `WISE_RUNTIME=SKIP` si WISE est volontairement desactive ;
- si Arkime Live est actif, `ARKIME_LIVE_NODE_HOST` non vide et Viewer joignable sur `8005/tcp` ;
- secret Arkime partage importe depuis le bundle Core.

Une requete manuelle OpenSearch sans identifiants peut retourner `401` : cela
confirme la connectivite et TLS mais pas les droits. La recette d'ingestion est
le controle fonctionnel final.

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

Apres redemarrage :

```bash
cd ~/oculox-collector
./oculox start
./oculox status
./oculox logs filebeat
```

Pendant une indisponibilite temporaire du Core, Filebeat met les evenements en
file puis reprend. Surveiller le disque pendant une panne longue.

## 9. Depannage Et Recette Finale

| Symptome | Cause probable | Action |
|---|---|---|
| bundle refuse | nom/host differents | reprendre les valeurs exactes |
| checksum invalide | transfert incomplet | recopier le bundle |
| Filebeat refuse TLS | CA, heure ou host incorrect | verifier bundle et horloge |
| aucun evenement | interface sans trafic | verifier SPAN/TAP et compteurs RX |
| PCAP duplique | plusieurs moteurs actifs | garder un seul moteur PCAP |
| `Error talking to node` dans Arkime | hote `8005` injoignable ou secret Arkime different | verifier `Arkime Node Host`, pare-feu et regenerer/recopier le bundle Core |
| Docker permission denied | groupe non recharge | reconnecter puis `resume-install` |

Le Collecteur est accepte lorsque les deux bundles passent, les services sont
sains, l'interface recoit du trafic, Filebeat utilise 5044/5045 avec verification
TLS complete, la recette retourne `INGESTION_RESULT=PASS` et un redemarrage de
VM remet automatiquement le service en fonctionnement.

Documentation complementaire :

- `dev/docs/13_installation_resiliente_principal_hedgehog.md` ;
- `dev/docs/Opensearch/guide_installation_vm_neuves.md` ;
- `docs/UPSTREAM_README.md`.
