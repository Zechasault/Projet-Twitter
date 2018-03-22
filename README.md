# INFO 901 Twitter : Détection de communautés

## Introduction

De nombreuses étapes sont nécessaires afin d'obtenir un graphe permettant de détecter des communautés au sein des utilisateurs de twitter, nous proposons dans ce document de faire part de nos étapes et réflexions afin de constituer une communauté de personnes parlant du véganisme.

Toutes les sources du projet sont disponibles sur github à l’adresse :

**[https://github.com/Zechasault/Projet-Twitte**r](https://github.com/Zechasault/Projet-Twitter)

Et le résultat à l’adresse :

**[https://zechasault.github.io/Projet-Twitter/web/community-networks.htm**l](https://zechasault.github.io/Projet-Twitter/web/community-networks.html)

Le travail effectué est découpé en 5 grandes étapes toutes décrites en détail plus bas :

* Étape 1 : Récupération et ajouts de tweets et utilisateurs en relation avec un topic depuis l'API dans une base de données redis 

* Étape 2 : Traitement du texte des tweets (nettoyage, tokenisation, suppression des stops word et stemmisation)

* Étape 3 : Ajout des informations dans une base de données Neo4j

* Étape 4 : Création des relations (direct et indirect) entre les différents utilisateurs

* Étape 5 : Création et visualisation du graphe de communautés

## Étape 1 : Récupération des tweets et utilisateurs

Outils utilisés: Python, Tweepy, Redis

Code: tweetStreamVaccum.py (https://github.com/Zechasault/Projet-Twitter/blob/master/python/tweetStreamVaccum.py)

Dans cette étape nous allons créer un stream permettant de récupérer tous les utilisateurs et tous les tweets (en langue anglaise) publiés en temps réel sur le sujet voulu, grâce au code contenu dans *"**tweetStreamVaccum.py"*.

Création du stream en temps réel permettant de récupérer les tweets :

![image alt text](https://zechasault.github.io/Projet-Twitter/screen/image_0.png)

Pour chaques tweets on va aller récupérer tous les utilisateurs en relation avec celui-ci

C’est à dire :

* Le créateur du tweet

* Tous les utilisateurs mentionnés dans le tweet

* L'utilisateur à qui le créateur a répondu

![image alt text](https://zechasault.github.io/Projet-Twitter/screen/image_1.png)

	

On va aussi récupérer : 

* Pour tous les retweets, les tweets originels

* Pour toutes les réponses de tweets, les tweets auquel il a répondu

![image alt text](https://zechasault.github.io/Projet-Twitter/screen/image_2.png)

Une fois les informations récupérées, on les ajoute dans une base de données redis, les utilisateur avec la clé "users" et pour les tweet la clé “tweets”.

Ainsi à l'exécution du script, la base de données se remplit petit à petit de tweets et utilisateurs.

![image alt text](https://zechasault.github.io/Projet-Twitter/screen/image_3.png)

          Exécution du script **_tweetStreamVaccum.py _**avec le topic vegan

## Étape 2 : Traitement du texte des tweets

Outils utilisés : Python, NLTK

Code : redisToNeo4j.py (https://github.com/Zechasault/Projet-Twitter/blob/master/python/redisToNeo4j.py)

Dans cette étape nous allons traiter les textes des tweets afin de récupérer la racine (stem) des mots contenus dans chacuns des tweets.

Cette étape est elle même constitué de plusieurs étapes décrite ci-dessous

Premièrement nous supprimons les éventuelles urls présents dans le texte grâce à une regex

*# Remove urls*

text = re.sub(**r'\w+:\/{2}[\d\w-]+(\.[\d\w-]+)*(?:(?:\/[^\s/]*))*'**, **''**, tweetContent.get(**"text"**).translate(non_bmp_map))

Nous supprimons aussi les hashtags et mentions qui ne font pas partie des stems et qui seront traité différemment dans l’étape 3

*# Clean text*

raw = **" "**.join(filter(**lambda **x:x[0]!=**'@'**, text.lower().split()))

raw = **" "**.join(filter(**lambda **x:x[0]!=**'#'**, raw.split()))

Une fois nettoyé des hashtags et mentions nous isolons chacun des mots constituant le texte dans une liste pour ensuite aller supprimer les stops word contenu dans dans celle-ci

*# Tokenize text*

tokens = tokenizer.tokenize(raw)

*# Remove stop words from tokens*

stopped_tokens = [text **for **text **in **tokens **if not **text **in **en_stop]

Une fois la liste ôtée des stops word nous transformons les mots la constituant en leur racine grâce à la fonction *p_stemmer.stem()* disponible dans le librairie nltk

*# Stem tokens*

stemmed_tokens = [p_stemmer.stem(text) **for **text **in **stopped_tokens]

## Étape 3 :  Ajout des informations dans une base de données neo4j

Outils utilisés : Python, Neo4j, Redis

Code : redisToNeo4j.py (https://github.com/Zechasault/Projet-Twitter/blob/master/python/redisToNeo4j.py)

Pour simplifier la constitution de graphes nous avons optés de sauvegarder toutes les données dans Neo4j ( c’est une base de données orientée graphes ).

Cette étape consiste donc à extraire les informations importante des tweets et utilisateur afin de peupler la base de données Neo4j de noeud et relation.

Avant de commencer cette étape il a fallu décider de la structure que la base Neo4j et des données elles mêmes

#### **Structure de la base de données :**

![image alt text](https://zechasault.github.io/Projet-Twitter/screen/image_4.png)

     **Structure de notre base de données Neo4j**

#### **Structure d’un Tweet :**

Un **Tweet **contient les informations suivantes :

* created_at      // Date de création

* favorite_count  

* source          // Support sur lequel le tweet a été publié

* id

* text

* Retweet_count   // Nombre de retweet

Un **Tweet **est relié avec :

* Les tags utilisés pour créer le tweet (relation **Tags**)

* Les urls contenus dans le texte (relation **Links**)

* Les racines des mots (stem) du texte (relation **Has**)

* Le langage du texte (relation **Written_in**)

* Différents utilisateurs :

    * Le créateur du tweet (relation **Tweeted_by**)

    * Les personnes qui ont retweeter le tweet (relation **ReTweeted_by**)

    * Les comptes mentionnés dans le tweet (relation **Mentions**)

#### **Structure d’un User:**

Un **User **contient les informations suivantes :

* friends_count

* favourites_count

* verified

* description

* created_at

* profile_image_url

* screen_name

* statuses_count

* followers_count

* name

* location

* Id

Un **User **est relié soit directement soit indirectement avec d’autres user.

U1 et U2 sont sont reliés entre eux **directement **lorsque:

- U1 a **répondu **à un tweet de U2

- U1 a **mentionné **U2 dans un de ses tweets

- U1 a **retweeté **un tweet de U2

U1 et U2 sont sont reliés entre eux **indirectement **lorsque:

- U1 et U2 ont publiés un tweet contenant 1 **Hashtags **identique

- U1 et U2 ont publiés un tweet contenant 1 **URL **identique

- U1 et U2 ont publiés un tweet contenant 3 **stems **identique

Une fois la structure de la base choisis il a fallu la remplir, pour ce faire un script python (redisToNeo4j.py) s’en charge. Ce script a pour but de :

1.  Récupérer les tweets et utilisateurs contenus dans Redis

2.  Extraire les informations des utilisateurs et tweets

3.  D’ajouter les informations extraites dans la base Neo4j

On traite d'abord les utilisateurs en créant un dictionnaire que l’on va remplir

u = {}

u[**"id"**] = userJson.get(**"id_str"**)

u[**"url"**] = userJson.get(**"url"**)

u[**"name"**] = userJson.get(**"name"**)

...

u_data = json.loads(json.dumps(u))

Puis nous créons la query correspondant à l’ajout d’un user dans la base **Neo4j**

query = **"""**

**WITH {json} as json**

**MERGE (u:User {id:json.id})**

**SET u = json**

**"""**

Note : **Merge **nous garantit l’unicité de l’utilisateur

Pour enfin l'exécuter :

g.run(query, json=u_data)

Le même procédé est utilisé pour sauvegarder les tweets mais nous ajoutons en plus les relations 

Par exemple, dans la query suivante on ajoute la relation d’un tweet a son langage

**MERGE (t)-[:WRITTEN_IN]->(l)**

Ainsi que la relation d’un tweet avec son créateur

**MERGE (t)-[:TWEETED_BY]->(u)**

query = **"""**

**WITH {json} as json**

**MERGE (t:Tweet {id:json.tweet.id})**

**SET t = json.tweet**

**MERGE (l:Language {code:json.language})**

**MERGE (u:User{id:json.tweet.userid})**

**MERGE (t)-[:WRITTEN_IN]->(l)**

**MERGE (t)-[:TWEETED_BY]->(u)**

**"""**

On ajoute, ainsi de suite tous les noeud et lien qui constituera la base

Note :  1. Seul les tweets originel sont sauvegardées ( par exemple, pour les retweets, seulement la relation RETWEETED_BY est créée)

	2. La création des relations direct et indirect entre user n’est pas effectuée ici et est expliqué à l'étape 4

## Étape 4 : Création des relations (directes et indirectes) entre les différents utilisateurs

L’ajout des relations est effectué par des requêtes cypher à la base Neo4j (auparavant remplis dans l’étape 3)

Elles sont disponible à l’adresse suivante :  

[https://github.com/Zechasault/Projet-Twitter/blob/master/web/query/query.cypher](https://github.com/Zechasault/Projet-Twitter/blob/master/web/query/query.cypher)

Prenons par exemple la query créant les relations direct entre les utilisateurs se répondant 

MATCH (u2:User)<-[:TWEETED_BY]-(reply:Tweet)-[:REPLIED_TO]->(t:Tweet)-[:TWEETED_BY]->(u1:User) 

WHERE u1 <> u2 

MERGE (u2)-[:DIRECT_REPLY]->(u1)

Avec le **_MATCH _**on va récupérer l’utilisateur **_u1 _**ayant tweeté un tweet **_t_**

(t:Tweet)-[:TWEETED_BY]->(u1:User) 

On identifie aussi le tweet **_reply _**qui correspond à une des réponses à* ***_t _**

(reply:Tweet)-[:REPLIED_TO]->(t:Tweet)

Et on récupère u2 qui est simplement le créateur du tweet **_reply_**

(u2:User)<-[:TWEETED_BY]-(reply:Tweet)

Le **_WHERE _**va simplement vérifier si u1 et u2 sont 2 utilisateurs différents (dans twitter il est possible de répondre à un de ses tweets)

WHERE u1 <> u2 

Et enfin le **MERGE **va créer le lien **DIRECT_REPLY **entre u1 et u2 si le where est "vérifié"

MERGE (u2)-[:DIRECT_REPLY]->(u1)

## Étape 5 : Création et visualisation du graphe de communautés

Outils : html/css, Javascript, vis.js

Une fois la base Neo4j remplis et les relations (directe et indirecte) créées, nous avons récupéré le graphe grâce à une query et affiché sur une page web.

L’affichage a été faite grâce à la librairie javascript **Vis.js**

Cette librairie simplifie grandement l’affichage de graphe, customisable à souhait il est possible de créer des affichages complexe très facilement.

On a testé plusieur affichage:

Toutes disponible aux adresses suivant :

Direct-networks : [https://zechasault.github.io/Projet-Twitter/web/indirect-user-networks.html](https://zechasault.github.io/Projet-Twitter/web/indirect-user-networks.html)

Indirect-networks :[https://zechasault.github.io/Projet-Twitter/web/direct-user-networks.html](https://zechasault.github.io/Projet-Twitter/web/direct-user-networks.html)

Community-networks : [https://zechasault.github.io/Projet-Twitter/web/community-networks.html](https://zechasault.github.io/Projet-Twitter/web/community-networks.html)

Dans le premier nous avons affiché tous les utilisateurs relier entre eux avec les relations indirect (**INDIRECT_HASHTAG, INDIRECT_STEM,  INDIRECT_URL**)

Grace à la query :

 

**"MATCH p=(u1)-[:INDIRECT_HASHTAG|:INDIRECT_STEM|:INDIRECT_URL]->(u2) RETURN p"**

![image alt text](https://zechasault.github.io/Projet-Twitter/screen/image_5.png)

Le second affiche les utilisateurs reliés entre eux avec les relations direct (**DIRECT_MENTION, DIRECT_REPLY, DIRECT_RETWEET**)

Grace à la query :

 

**"MATCH p=(u1)-[:DIRECT_RETWEET|:DIRECT_MENTION|:DIRECT_REPLY]->(u2) RETURN p"**

![image alt text](https://zechasault.github.io/Projet-Twitter/screen/image_6.png)

Le dernier affiche la combinaison des deux graphes précédemment

Grace à la query :

 

**"****MATCH p=(u1)-[:DIRECT_RETWEET|:DIRECT_MENTION|:DIRECT_REPLY|INDIRECT_HASHTAG**

**|:INDIRECT_STEM|:INDIRECT_URL]->(u2) RETURN p****"**

![image alt text](https://zechasault.github.io/Projet-Twitter/screen/image_7.png)

Avec ces visualisations on peut très clairement distinguer les différents groupes que peuvent former les utilisateur

## Popoto

Nous avons aussi utilisé l'interface de recherche [Popoto.js](http://popotojs.com/) sur notre base de donnée **Neo4J, **nous permettant de faire des recherches graphiquement dans toutes les données en sélectionnant les filtres qui nous intéressent.

Exemple live disponible ici:

[https://zechasault.github.io/Projet-Twitter/web/popoto.html](https://zechasault.github.io/Projet-Twitter/web/popoto.html)

Par exemple nous allons pouvoir rechercher tous les tweets qui contiennent les Hashtags **#vegan** et **#vegetarian** très facilement, il suffit de sélectionner la relation **Tags**, (matérialisé par 1/8 de cercle rose situé autour du noeud tweet) et aller récupérer le tags correspondant en cliquant sur le noeud **TAGS**

La query exécutée est disponible dans la partie **Query**

Et les résultats dans la partie **Résults**

![image alt text](https://zechasault.github.io/Projet-Twitter/screen/image_8.png)

## Sources :

* NLTK :  [https://www.nltk.org](https://www.nltk.org)

* REDIS : [https://redis.io](https://redis.io)

* Neo4J : [https://neo4j.com](https://neo4j.com)

* Py2neo : [http://py2neo.org/](http://py2neo.org/)

* VIS.js : http://visjs.org

* Popoto : [http://www.popotojs.com](http://www.popotojs.com)

