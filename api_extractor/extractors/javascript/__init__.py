"""JavaScript/TypeScript framework extractors."""

from api_extractor.extractors.javascript.express import ExpressExtractor
from api_extractor.extractors.javascript.fastify import FastifyExtractor
from api_extractor.extractors.javascript.nestjs import NestJSExtractor
from api_extractor.extractors.javascript.nextjs import NextJSExtractor

__all__ = ["ExpressExtractor", "FastifyExtractor", "NestJSExtractor", "NextJSExtractor"]
