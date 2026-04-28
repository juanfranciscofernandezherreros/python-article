package com.github.juanfernandez.article;

import com.github.juanfernandez.article.article.application.ArticleGeneratorService;
import com.github.juanfernandez.article.article.application.PromptBuilderService;
import com.github.juanfernandez.article.article.application.SeoService;
import com.github.juanfernandez.article.article.application.TextUtils;
import com.github.juanfernandez.article.article.port.in.ArticleGeneratorPort;
import com.github.juanfernandez.article.shared.ai.port.AiPort;
import com.github.juanfernandez.article.shared.config.ArticleGeneratorProperties;
import com.github.juanfernandez.article.shared.util.JsonUtils;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;

/**
 * Spring Boot auto-configuration for the article bounded context.
 *
 * <p>Builds on top of {@link AiAutoConfiguration}: the AI-related beans
 * ({@link AiPort}, {@link JsonUtils}, …) are produced there and consumed here.  This class
 * focuses on the article-specific application services and their primary port.
 *
 * <p>Question generation ({@code PreguntaGeneratorService}) is handled separately by
 * {@link PreguntaGeneratorAutoConfiguration}, which is only activated when a
 * {@code JpaPreguntaRepository} bean is present.
 *
 * <p>Activated automatically via
 * {@code META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports}.
 */
@AutoConfiguration(after = AiAutoConfiguration.class)
@EnableConfigurationProperties(ArticleGeneratorProperties.class)
public class ArticleGeneratorAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public TextUtils textUtils() {
        return new TextUtils();
    }

    @Bean
    @ConditionalOnMissingBean
    public SeoService seoService(ArticleGeneratorProperties properties) {
        return new SeoService(properties);
    }

    @Bean
    @ConditionalOnMissingBean
    public PromptBuilderService promptBuilderService(ArticleGeneratorProperties properties) {
        return new PromptBuilderService(properties);
    }

    @Bean
    @ConditionalOnMissingBean(ArticleGeneratorPort.class)
    public ArticleGeneratorService articleGeneratorService(
            ArticleGeneratorProperties properties,
            AiPort aiPort,
            PromptBuilderService promptBuilderService,
            SeoService seoService,
            TextUtils textUtils,
            JsonUtils jsonUtils) {
        return new ArticleGeneratorService(
                properties, aiPort, promptBuilderService, seoService, textUtils, jsonUtils);
    }
}
