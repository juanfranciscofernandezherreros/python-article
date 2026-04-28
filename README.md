# ai-generic-generation-content

Spring Boot starter library for AI-powered content generation.

Two main capabilities:
- **Article generation** — technical articles with full SEO metadata via `ArticleGeneratorService`.
- **Question generation** — multilingual questionnaire questions persisted in PostgreSQL via `PreguntaGeneratorService`.

Supported AI providers (via **LangChain4j** or direct REST fallback):  
**OpenAI (GPT)** · **Google Gemini** · **Ollama (local)** · **Anthropic Claude**

---

## Contents

- [Requirements](#requirements)
- [Add the dependency](#add-the-dependency)
- [Configure an AI provider](#configure-an-ai-provider)
- [Use ArticleGeneratorService](#use-articlegeneratorservice)
- [Use PreguntaGeneratorService](#use-preguntaGeneratorservice)
- [Properties reference](#properties-reference)
- [Article model reference](#article-model-reference)
- [ArticleRequest reference](#articlerequest-reference)
- [Pregunta model reference](#pregunta-model-reference)
- [Title deduplication algorithm](#title-deduplication-algorithm)
- [Quick notes](#quick-notes)

---

## Requirements

| | Minimum |
|---|---|
| Java | 17 |
| Maven | 3.9 |
| Spring Boot (consuming app) | 3.x |

---

## Add the dependency

Install the library to your local Maven repository from the repo root:

```bash
cd ai-generic-generation-content
mvn clean install
```

Then add it to your Spring Boot project's `pom.xml`:

```xml
<dependency>
    <groupId>io.github.aigen</groupId>
    <artifactId>ai-generic-generation-content</artifactId>
    <version>0.1.0</version>
</dependency>
```

The LangChain4j provider starters are declared `optional` in this library.  
Add the one you need in **your** project:

```xml
<!-- OpenAI -->
<dependency>
    <groupId>dev.langchain4j</groupId>
    <artifactId>langchain4j-open-ai-spring-boot-starter</artifactId>
    <version>1.0.0-beta5</version>
</dependency>

<!-- Google Gemini -->
<dependency>
    <groupId>dev.langchain4j</groupId>
    <artifactId>langchain4j-google-ai-gemini-spring-boot-starter</artifactId>
    <version>1.0.0-beta5</version>
</dependency>

<!-- Ollama -->
<dependency>
    <groupId>dev.langchain4j</groupId>
    <artifactId>langchain4j-ollama-spring-boot-starter</artifactId>
    <version>1.0.0-beta5</version>
</dependency>

<!-- Anthropic Claude -->
<dependency>
    <groupId>dev.langchain4j</groupId>
    <artifactId>langchain4j-anthropic-spring-boot-starter</artifactId>
    <version>1.0.0-beta5</version>
</dependency>
```

---

## Configure an AI provider

### Option A — OpenAI via LangChain4j ✅ Recommended

```yaml
langchain4j:
  open-ai:
    chat-model:
      api-key: ${OPENAIAPIKEY}
      model-name: gpt-4o
      temperature: 0.7
      timeout: PT60S
      log-requests: true
      log-responses: true

article-generator:
  site: https://myblog.com
  author-username: adminUser
  language: en
```

The starter auto-detects the `ChatModel` bean created by LangChain4j.  
No need to set `article-generator.provider` or `article-generator.openai-api-key`.

### Option B — Google Gemini via LangChain4j ✅ Recommended

```yaml
langchain4j:
  google-ai-gemini:
    chat-model:
      api-key: ${GEMINI_API_KEY}
      model-name: gemini-2.0-flash
      temperature: 0.7
      log-requests: true
      log-responses: true

article-generator:
  site: https://myblog.com
  author-username: adminUser
  language: en
```

### Option C — Ollama via LangChain4j ✅ Recommended

```yaml
langchain4j:
  ollama:
    chat-model:
      base-url: http://localhost:11434
      model-name: llama3
      temperature: 0.7
      timeout: PT120S

article-generator:
  site: https://myblog.com
  author-username: adminUser
  language: en
```

### Option D — Anthropic Claude via LangChain4j ✅ Recommended

Requires `langchain4j-anthropic-spring-boot-starter` on the classpath.  
Anthropic has no direct REST fallback — LangChain4j is mandatory.

```yaml
langchain4j:
  anthropic:
    chat-model:
      api-key: ${ANTHROPIC_API_KEY}
      model-name: claude-sonnet-4-5
      temperature: 0.7
      timeout: PT60S
      log-requests: true
      log-responses: true

article-generator:
  provider: anthropic
  site: https://myblog.com
  author-username: adminUser
  language: en
```

### Option E — OpenAI direct REST (no LangChain4j)

```yaml
article-generator:
  provider: openai
  model: gpt-4o
  openai-api-key: ${OPENAIAPIKEY}
  site: https://myblog.com
  author-username: adminUser
  language: en
```

### Option F — Google Gemini direct REST (no LangChain4j)

```yaml
article-generator:
  provider: gemini
  model: gemini-2.0-flash
  gemini-api-key: ${GEMINI_API_KEY}
  site: https://myblog.com
  author-username: adminUser
  language: en
```

### Option G — Ollama direct REST (no LangChain4j)

```yaml
article-generator:
  provider: ollama
  model: llama3
  ollama-base-url: http://localhost:11434
  site: https://myblog.com
  author-username: adminUser
  language: en
```

### Auto-detection (`AUTO`)

When `article-generator.provider` is not set (or left as `AUTO`) the starter picks the provider in this order:

1. If a LangChain4j `ChatModel` bean is present → use it.
2. Else if `article-generator.model` starts with `gemini-` → Gemini REST.
3. Else if `article-generator.ollama-base-url` is set → Ollama REST.
4. Otherwise → OpenAI REST (requires `article-generator.openai-api-key`).

---

## Use ArticleGeneratorService

Inject `ArticleGeneratorService` (from `io.github.aigen.article.application`) and call `generateArticle(ArticleRequest)`.

```java
import io.github.aigen.article.application.ArticleGeneratorService;
import io.github.aigen.article.domain.Article;
import io.github.aigen.article.domain.ArticleRequest;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/articles")
public class ArticleController {

    private final ArticleGeneratorService articleGeneratorService;

    public ArticleController(ArticleGeneratorService articleGeneratorService) {
        this.articleGeneratorService = articleGeneratorService;
    }

    @PostMapping("/generate")
    public Article generate(@RequestBody GenerateArticleInput input) {
        ArticleRequest request = ArticleRequest.builder()
                .category(input.category())          // required
                .subcategory(input.subcategory())
                .tag(input.tag())
                .title(input.title())                // optional: fixes the title; skips deduplication
                .language(input.language())
                .site(input.site())
                .authorUsername(input.authorUsername())
                .avoidTitles(input.avoidTitles())    // titles the AI must not reproduce
                .build();

        return articleGeneratorService.generateArticle(request);
    }

    public record GenerateArticleInput(
            String category,
            String subcategory,
            String tag,
            String title,
            String language,
            String site,
            String authorUsername,
            List<String> avoidTitles
    ) {}
}
```

**Minimal example:**

```java
Article article = articleGeneratorService.generateArticle(
    ArticleRequest.builder()
        .category("Spring Boot")
        .subcategory("Spring Security")
        .tag("JWT Authentication")
        .build()
);

System.out.println(article.getTitle());
System.out.println(article.getBody());
System.out.println(article.getCanonicalUrl());
```

**Sample curl call:**

```bash
curl -X POST http://localhost:8080/api/articles/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "category": "Spring Boot",
    "subcategory": "Spring Security",
    "tag": "JWT Authentication",
    "language": "en",
    "site": "https://myblog.com",
    "authorUsername": "alice",
    "avoidTitles": ["Introduction to JWT", "JWT basics"]
  }'
```

**Sample response:**

```json
{
  "title": "JWT Authentication in Spring Boot 3: a practical guide",
  "slug": "jwt-authentication-in-spring-boot-3-a-practical-guide",
  "summary": "Learn how to implement JWT in Spring Boot 3 with best practices.",
  "body": "<h1>JWT Authentication in Spring Boot 3: a practical guide</h1>...",
  "category": "Spring Security",
  "tags": ["JWT Authentication"],
  "author": "alice",
  "status": "published",
  "isVisible": true,
  "keywords": ["jwt spring boot", "spring security", "token"],
  "metaTitle": "JWT Authentication in Spring Boot 3: a practical guide",
  "metaDescription": "Learn how to implement JWT in Spring Boot 3 with best practices.",
  "canonicalUrl": "https://myblog.com/post/jwt-authentication-in-spring-boot-3-a-practical-guide",
  "structuredData": {
    "@context": "https://schema.org",
    "@type": "TechArticle",
    "headline": "JWT Authentication in Spring Boot 3: a practical guide",
    "author": { "@type": "Person", "name": "alice" },
    "url": "https://myblog.com/post/jwt-authentication-in-spring-boot-3-a-practical-guide"
  },
  "ogTitle": "JWT Authentication in Spring Boot 3: a practical guide",
  "ogDescription": "Learn how to implement JWT in Spring Boot 3 with best practices.",
  "ogType": "article",
  "wordCount": 1300,
  "readingTime": 7,
  "publishDate": "2026-04-28T10:00:00Z",
  "createdAt": "2026-04-28T10:00:00Z",
  "updatedAt": "2026-04-28T10:00:00Z",
  "generatedAt": "2026-04-28T10:00:00Z"
}
```

---

## Use PreguntaGeneratorService

**Additional requirements:** `spring-boot-starter-data-jpa` on the classpath and a PostgreSQL `DataSource` configured.  
The `PreguntaGeneratorService` and `PreguntaRepository` beans are only registered when both conditions are met.

### 1. Add JPA + PostgreSQL dependencies

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-jpa</artifactId>
</dependency>
<dependency>
    <groupId>org.postgresql</groupId>
    <artifactId>postgresql</artifactId>
    <scope>runtime</scope>
</dependency>
```

### 2. Configure the data source

```yaml
spring:
  datasource:
    url: jdbc:postgresql://localhost:5432/mydb
    username: ${DB_USER}
    password: ${DB_PASSWORD}
  jpa:
    hibernate:
      ddl-auto: validate
```

### 3. Create the `preguntas` table

```sql
CREATE TABLE preguntas (
    id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    campo          VARCHAR(255) NOT NULL,
    orden          INTEGER      NOT NULL,
    texto          JSONB        NOT NULL,
    actualizada_en TIMESTAMPTZ  NOT NULL DEFAULT now()
);
```

### 4. Inject and call the service

```java
import io.github.aigen.pregunta.application.PreguntaGeneratorService;
import io.github.aigen.pregunta.domain.Pregunta;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/preguntas")
public class PreguntaController {

    private final PreguntaGeneratorService preguntaGeneratorService;

    public PreguntaController(PreguntaGeneratorService preguntaGeneratorService) {
        this.preguntaGeneratorService = preguntaGeneratorService;
    }

    /**
     * Generates a new unique multilingual question and persists it in the `preguntas` table.
     */
    @PostMapping("/generate")
    public Pregunta generate() {
        return preguntaGeneratorService.generateAndSave();
    }
}
```

**Sample curl call:**

```bash
curl -X POST http://localhost:8080/api/preguntas/generate
```

**Sample response:**

```json
{
  "id": "63838a84-01e6-4fab-ac9b-3906a92fc29d",
  "campo": "viviendaAlquiler",
  "orden": 7,
  "texto": {
    "ca": "Vius de lloguer?",
    "en": "Do you live in a rented home?",
    "es": "¿Vives de alquiler?",
    "fr": "Vivez-vous en location?"
  },
  "actualizadaEn": "2026-04-28T10:00:00+00:00"
}
```

---

## Properties reference

All properties use the prefix `article-generator`.

### AI provider

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `provider` | `AUTO` \| `OPENAI` \| `GEMINI` \| `OLLAMA` \| `ANTHROPIC` | `AUTO` | Active AI provider |
| `model` | `String` | `gpt-4o` | Model name |
| `openai-api-key` | `String` | — | OpenAI API key |
| `gemini-api-key` | `String` | — | Google Gemini API key |
| `ollama-base-url` | `String` | — | Ollama base URL (e.g. `http://localhost:11434`) |

### Article defaults

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `site` | `String` | `""` | Base URL for canonical links |
| `author-username` | `String` | `adminUser` | Default author |
| `language` | `String` | `es` | Default language (ISO 639-1) |
| `output-dir` | `String` | — | Directory to write `<slug>.json` files; unset = no disk write |

### AI generation parameters

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `temperature-article` | `double` | `0.7` | Temperature for article body (0.0–1.0) |
| `temperature-title` | `double` | `0.9` | Temperature for title-only regeneration (0.0–1.0) |
| `max-article-tokens` | `int` | `8096` | Max output tokens for full article |
| `max-title-tokens` | `int` | `100` | Max output tokens for title-only |

### Deduplication & retries

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `similarity-threshold` | `double` | `0.86` | LCS similarity above which a title is a duplicate |
| `max-title-retries` | `int` | `5` | Max attempts to regenerate a unique title (Phase 2) |
| `max-api-retries` | `int` | `3` | Max retries for transient AI API errors |
| `retry-base-delay-seconds` | `int` | `2` | Base delay (seconds) for exponential back-off |

### SEO metadata limits

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `meta-title-max-length` | `int` | `60` | Max length of `metaTitle` |
| `meta-description-max-length` | `int` | `160` | Max length of `metaDescription` |
| `max-avoid-titles-in-prompt` | `int` | `5` | Max avoid-titles sent to the AI in one prompt |

### Custom system messages

| Property | Type | Description |
|----------|------|-------------|
| `generation-system-msg` | `String` | Overrides the built-in system message for article generation |
| `title-system-msg` | `String` | Overrides the built-in system message for title-only generation |

### Custom prompt templates

| Property | Placeholders | Description |
|----------|--------------|-------------|
| `generation-prompt-template` | `{lang}`, `{topic}`, `{parentName}`, `{subcatName}`, `{titleInstruction}`, `{avoidBlock}` | Full article prompt |
| `title-prompt-template` | `{lang}`, `{topic}`, `{parentName}`, `{subcatName}`, `{maxLen}`, `{avoidBlock}` | Title-only prompt |

---

## Article model reference

`io.github.aigen.article.domain.Article`

| Field | Type | Description |
|-------|------|-------------|
| `title` | `String` | SEO-optimised article title |
| `slug` | `String` | URL-safe slug derived from the title |
| `summary` | `String` | Meta-description (≤ 160 chars recommended) |
| `body` | `String` | Full article body as semantic HTML |
| `category` | `String` | Sub-category name |
| `tags` | `List<String>` | Topic tags |
| `author` | `String` | Author username |
| `status` | `String` | Always `"published"` |
| `isVisible` | `boolean` | Always `true` |
| `keywords` | `List<String>` | Long-tail SEO keywords |
| `metaTitle` | `String` | Truncated title for `<title>` tag |
| `metaDescription` | `String` | Truncated summary for meta-description |
| `canonicalUrl` | `String` | `{site}/post/{slug}` |
| `structuredData` | `Map<String, Object>` | Schema.org `TechArticle` JSON-LD |
| `ogTitle` | `String` | Open Graph title |
| `ogDescription` | `String` | Open Graph description |
| `ogType` | `String` | Always `"article"` |
| `wordCount` | `int` | Approximate word count |
| `readingTime` | `int` | Estimated reading time in minutes |
| `publishDate` | `String` | ISO 8601 UTC |
| `createdAt` | `String` | ISO 8601 UTC |
| `updatedAt` | `String` | ISO 8601 UTC |
| `generatedAt` | `String` | ISO 8601 UTC |

---

## ArticleRequest reference

`io.github.aigen.article.domain.ArticleRequest`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `category` | `String` | ✅ | Article category |
| `subcategory` | `String` | No | Sub-category (default: `"General"`) |
| `tag` | `String` | No | Topic / tag |
| `title` | `String` | No | Forces an exact title; the AI generates the body around it and deduplication is skipped |
| `authorUsername` | `String` | No | Overrides `article-generator.author-username` for this request |
| `site` | `String` | No | Overrides `article-generator.site` for this request |
| `language` | `String` | No | ISO 639-1 code; overrides `article-generator.language` |
| `avoidTitles` | `List<String>` | No | Titles the AI must not reproduce (used in deduplication) |

---

## Pregunta model reference

`io.github.aigen.pregunta.domain.Pregunta` — JPA entity mapped to the `preguntas` table.

| Field | Java type | PostgreSQL column | Description |
|-------|-----------|-------------------|-------------|
| `id` | `UUID` | `UUID PRIMARY KEY DEFAULT gen_random_uuid()` | Database-assigned identifier |
| `campo` | `String` | `VARCHAR(255) NOT NULL` | camelCase field identifier (e.g. `viviendaAlquiler`) |
| `orden` | `Integer` | `INTEGER NOT NULL` | Display order (1-based) |
| `texto` | `Map<String, String>` | `JSONB NOT NULL` | Question text per locale: `ca`, `en`, `es`, `fr` |
| `actualizadaEn` | `OffsetDateTime` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | Last-updated timestamp |

---

## Title deduplication algorithm

When `avoidTitles` is non-empty (and no explicit `title` is provided) the starter uses a two-phase approach:

**Phase 1 — Full article generation**

1. The AI generates the complete article (title + summary + HTML body + keywords).
2. The generated title is compared against every entry in `avoidTitles` using the LCS similarity metric: `2 × LCS / (|a| + |b|)` (equivalent to Python's `SequenceMatcher.ratio()`).
3. If all similarities are below `similarity-threshold` (default `0.86`) → article accepted, done.
4. If the title is too similar to an existing one → Phase 2.

**Phase 2 — Title-only regeneration**

1. The HTML body from Phase 1 is kept as-is.
2. The AI is asked to produce only a new title (up to `max-title-retries` attempts).
3. Each candidate is checked against `avoidTitles`.
4. The first title that passes is applied (the `<h1>` in the body is updated accordingly).
5. If no attempt produces a unique title an exception is thrown.

---

## Quick notes

- `category` is the only mandatory field in `ArticleRequest`.
- If `subcategory` is omitted, `"General"` is used.
- If `language`, `site`, or `authorUsername` are omitted in the request, the values from `application.yml` are used.
- If `title` is provided the AI generates the body around that exact title and deduplication is skipped entirely.
- `PreguntaGeneratorService` is only registered when `spring-boot-starter-data-jpa` and a PostgreSQL `DataSource` are on the classpath.
- `PreguntaGeneratorService.generateAndSave()` deduplicates automatically: it checks both the `campo` identifier and the Spanish text before persisting.
- All beans are `@ConditionalOnMissingBean` — you can override any bean in your consuming application.
