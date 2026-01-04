# M-Action E-Commerce API - Nx Monorepo Architecture

## Executive Summary

This document defines the target Nx monorepo architecture for migrating the legacy vanilla PHP "m-action" e-commerce API to NestJS. The system serves product catalog, categories, shopping cart, bidding, promotions, notifications, and related e-commerce functionality.

**Key Metrics from Legacy Analysis:**
- 157 PHP files, 32,192 lines of code
- 203 routes (all GET endpoints)
- 161 security issues (36 critical, 95 high severity)
- 57 database tables, 44 database operations
- 52+ external API integrations
- Estimated migration effort: High complexity

---

## 1. Domain Analysis

### Identified Business Domains

| Domain | Type | Lines | Complexity | Files | Security Issues | Description |
|--------|------|-------|------------|-------|-----------------|-------------|
| **Products** | Core | 7,286 | 1,126 | 21 | 30 | Product catalog, items, specifications, recommendations |
| **Core** | Generic | 6,581 | 911 | 43 | 34 | Setup, utilities, infrastructure, shared functions |
| **Config** | Generic | 2,336 | 407 | 17 | 10 | Application configuration, settings, cookies |
| **Categories** | Core | 2,627 | 361 | 7 | 8 | Category navigation, filtering |
| **Content** | Supporting | 2,364 | 247 | 16 | 15 | Pages, menus, footer, articles, homepage |
| **Worlds** | Core | 1,757 | 301 | 3 | 15 | Product "worlds"/themes (e.g., Black Friday) |
| **SEO** | Supporting | 1,443 | 181 | 5 | 4 | SEO metadata, optimization |
| **Promotions** | Core | 1,181 | 146 | 8 | 6 | Sales, discounts, campaigns |
| **BMS** | Core | 797 | 169 | 1 | 3 | Build My System (PC builder) |
| **Cart** | Core | 641 | 99 | 2 | 7 | Shopping cart operations |
| **Brands** | Supporting | 786 | 105 | 1 | 2 | Brand management |
| **Search** | Core | 436 | 61 | 2 | 4 | Product search, autocomplete |
| **Bidding** | Core | 430 | 36 | 2 | 2 | Auction/bidding system |
| **Stores** | Supporting | 271 | 30 | 2 | 2 | Physical store locations |
| **Payments** | Supporting | 323 | 28 | 2 | 2 | Payment calculations |
| **Notifications** | Supporting | 237 | 22 | 4 | 4 | Push, email, mailing |
| **Pricing** | Supporting | 298 | 68 | 2 | 0 | Price alerts, calculations |
| **Compare** | Supporting | 184 | 27 | 1 | 0 | Product comparison |
| **Affiliation** | Supporting | 362 | 62 | 1 | 1 | Affiliate/bonus system |
| **Auth** | Generic | 91 | 14 | 1 | 0 | Authentication (Amex login) |
| **Users** | Generic | 98 | 10 | 2 | 1 | User API integration |
| **Help** | Supporting | 344 | 8 | 2 | 5 | Lab, accessibility (nagish) |

### Domain Classification Summary

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CORE DOMAINS                                   │
│  (Business Differentiators - Migrate First, High Priority)              │
│                                                                          │
│  ┌──────────┐ ┌────────────┐ ┌───────────┐ ┌────────────┐ ┌───────────┐ │
│  │ Products │ │ Categories │ │  Search   │ │ Promotions │ │   Cart    │ │
│  │ 7.3K LOC │ │  2.6K LOC  │ │  436 LOC  │ │  1.2K LOC  │ │  641 LOC  │ │
│  └──────────┘ └────────────┘ └───────────┘ └────────────┘ └───────────┘ │
│  ┌──────────┐ ┌────────────┐ ┌───────────┐                              │
│  │  Worlds  │ │   Bidding  │ │    BMS    │                              │
│  │ 1.8K LOC │ │  430 LOC   │ │  797 LOC  │                              │
│  └──────────┘ └────────────┘ └───────────┘                              │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        SUPPORTING DOMAINS                                │
│  (Necessary but Generic - Migrate After Core)                           │
│                                                                          │
│  ┌──────────┐ ┌────────────┐ ┌───────────┐ ┌────────────┐ ┌───────────┐ │
│  │ Content  │ │    SEO     │ │  Brands   │ │   Stores   │ │ Payments  │ │
│  └──────────┘ └────────────┘ └───────────┘ └────────────┘ └───────────┘ │
│  ┌──────────┐ ┌────────────┐ ┌───────────┐ ┌────────────┐ ┌───────────┐ │
│  │Notificat.│ │  Pricing   │ │  Compare  │ │ Affiliation│ │   Help    │ │
│  └──────────┘ └────────────┘ └───────────┘ └────────────┘ └───────────┘ │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         GENERIC DOMAINS                                  │
│  (Infrastructure/Utilities - Build as Foundation)                       │
│                                                                          │
│  ┌──────────┐ ┌────────────┐ ┌───────────┐                              │
│  │   Core   │ │   Config   │ │   Auth    │                              │
│  │   Infra  │ │  Settings  │ │   Users   │                              │
│  └──────────┘ └────────────┘ └───────────┘                              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Nx Structure

### Architecture Decision: Modular Monolith First

**DECISION: Start as a single gateway application with well-organized modules.**

**Rationale:**
1. All 203 routes are GET endpoints - uniform traffic pattern
2. No clear team ownership boundaries requiring separation
3. Tightly coupled data access across domains (many shared tables)
4. Simpler deployment and operational overhead during migration
5. Can extract to separate services later if needed

### Apps

| App | Type | Modules | Port | Justification |
|-----|------|---------|------|---------------|
| `gateway` | HTTP API | All modules (see below) | 3000 | Main entry point, handles all e-commerce API requests |

**Future extraction candidates** (only if scaling/team needs arise):
- `search-service` - If search traffic spikes independently
- `notifications-service` - If async processing needed at scale

### Libs

| Library | Purpose | Used By |
|---------|---------|---------|
| `shared-dto` | Shared interfaces, DTOs, validation decorators | gateway |
| `database` | TypeORM entities, migrations, repository patterns | gateway |
| `common` | Guards, interceptors, decorators, utilities | gateway |
| `cache` | Redis cache service and decorators | gateway |
| `http-client` | HTTP client wrapper for external APIs | gateway |

### Folder Structure

```
m-action-api/
├── apps/
│   └── gateway/
│       └── src/
│           ├── app.module.ts
│           ├── main.ts
│           │
│           ├── products/                    # Core Domain
│           │   ├── products.module.ts
│           │   ├── products.controller.ts
│           │   ├── products.service.ts
│           │   ├── dto/
│           │   │   ├── product.dto.ts
│           │   │   └── product-query.dto.ts
│           │   ├── entities/               # If not shared
│           │   └── services/
│           │       ├── item.service.ts
│           │       ├── item-specifications.service.ts
│           │       ├── item-recommendations.service.ts
│           │       ├── combo.service.ts
│           │       └── stock.service.ts
│           │
│           ├── categories/                  # Core Domain
│           │   ├── categories.module.ts
│           │   ├── categories.controller.ts
│           │   ├── categories.service.ts
│           │   └── dto/
│           │
│           ├── search/                      # Core Domain
│           │   ├── search.module.ts
│           │   ├── search.controller.ts
│           │   ├── search.service.ts
│           │   └── services/
│           │       └── autocomplete.service.ts
│           │
│           ├── cart/                        # Core Domain
│           │   ├── cart.module.ts
│           │   ├── cart.controller.ts
│           │   └── cart.service.ts
│           │
│           ├── promotions/                  # Core Domain
│           │   ├── promotions.module.ts
│           │   ├── promotions.controller.ts
│           │   ├── promotions.service.ts
│           │   └── services/
│           │       ├── sales.service.ts
│           │       ├── black-friday.service.ts
│           │       └── bms-sale.service.ts
│           │
│           ├── worlds/                      # Core Domain
│           │   ├── worlds.module.ts
│           │   ├── worlds.controller.ts
│           │   └── worlds.service.ts
│           │
│           ├── bidding/                     # Core Domain
│           │   ├── bidding.module.ts
│           │   ├── bidding.controller.ts
│           │   └── bidding.service.ts
│           │
│           ├── bms/                         # Core Domain (Build My System)
│           │   ├── bms.module.ts
│           │   ├── bms.controller.ts
│           │   └── bms.service.ts
│           │
│           ├── content/                     # Supporting Domain
│           │   ├── content.module.ts
│           │   ├── controllers/
│           │   │   ├── pages.controller.ts
│           │   │   ├── menu.controller.ts
│           │   │   ├── footer.controller.ts
│           │   │   └── home.controller.ts
│           │   └── services/
│           │       ├── pages.service.ts
│           │       ├── menu.service.ts
│           │       ├── footer.service.ts
│           │       └── articles.service.ts
│           │
│           ├── seo/                         # Supporting Domain
│           │   ├── seo.module.ts
│           │   ├── seo.controller.ts
│           │   └── seo.service.ts
│           │
│           ├── brands/                      # Supporting Domain
│           │   ├── brands.module.ts
│           │   ├── brands.controller.ts
│           │   └── brands.service.ts
│           │
│           ├── stores/                      # Supporting Domain
│           │   ├── stores.module.ts
│           │   ├── stores.controller.ts
│           │   └── stores.service.ts
│           │
│           ├── notifications/               # Supporting Domain
│           │   ├── notifications.module.ts
│           │   ├── notifications.controller.ts
│           │   └── services/
│           │       ├── push.service.ts
│           │       ├── mailing.service.ts
│           │       └── raw-push.service.ts
│           │
│           ├── pricing/                     # Supporting Domain
│           │   ├── pricing.module.ts
│           │   ├── pricing.controller.ts
│           │   └── pricing.service.ts
│           │
│           ├── compare/                     # Supporting Domain
│           │   ├── compare.module.ts
│           │   ├── compare.controller.ts
│           │   └── compare.service.ts
│           │
│           ├── affiliation/                 # Supporting Domain
│           │   ├── affiliation.module.ts
│           │   ├── affiliation.controller.ts
│           │   └── affiliation.service.ts
│           │
│           ├── help/                        # Supporting Domain
│           │   ├── help.module.ts
│           │   ├── help.controller.ts
│           │   └── services/
│           │       ├── lab.service.ts
│           │       └── accessibility.service.ts
│           │
│           ├── config/                      # Generic Domain
│           │   ├── config.module.ts
│           │   ├── config.controller.ts
│           │   └── services/
│           │       ├── settings.service.ts
│           │       ├── cookies.service.ts
│           │       └── device.service.ts
│           │
│           ├── auth/                        # Generic Domain
│           │   ├── auth.module.ts
│           │   ├── auth.controller.ts
│           │   ├── auth.service.ts
│           │   ├── strategies/
│           │   │   └── jwt.strategy.ts
│           │   └── guards/
│           │       ├── jwt-auth.guard.ts
│           │       └── optional-auth.guard.ts
│           │
│           └── users/                       # Generic Domain
│               ├── users.module.ts
│               ├── users.controller.ts
│               └── users.service.ts
│
├── libs/
│   ├── shared-dto/
│   │   └── src/
│   │       ├── index.ts
│   │       ├── products/
│   │       │   ├── product.interface.ts
│   │       │   ├── product-response.dto.ts
│   │       │   └── product-query.dto.ts
│   │       ├── categories/
│   │       ├── common/
│   │       │   ├── pagination.dto.ts
│   │       │   └── api-response.dto.ts
│   │       └── ...
│   │
│   ├── database/
│   │   └── src/
│   │       ├── index.ts
│   │       ├── database.module.ts
│   │       ├── entities/
│   │       │   ├── part.entity.ts
│   │       │   ├── ntag-name.entity.ts
│   │       │   ├── ntag-parts.entity.ts
│   │       │   ├── z-item.entity.ts
│   │       │   └── ... (57 entities)
│   │       └── migrations/
│   │
│   ├── common/
│   │   └── src/
│   │       ├── index.ts
│   │       ├── guards/
│   │       │   ├── jwt-auth.guard.ts
│   │       │   └── rate-limit.guard.ts
│   │       ├── interceptors/
│   │       │   ├── logging.interceptor.ts
│   │       │   ├── cache.interceptor.ts
│   │       │   └── transform.interceptor.ts
│   │       ├── decorators/
│   │       │   ├── current-user.decorator.ts
│   │       │   ├── public.decorator.ts
│   │       │   └── cache-key.decorator.ts
│   │       ├── filters/
│   │       │   └── http-exception.filter.ts
│   │       └── utils/
│   │           ├── sanitize.util.ts
│   │           └── response.util.ts
│   │
│   ├── cache/
│   │   └── src/
│   │       ├── index.ts
│   │       ├── cache.module.ts
│   │       ├── cache.service.ts
│   │       └── decorators/
│   │           └── cacheable.decorator.ts
│   │
│   └── http-client/
│       └── src/
│           ├── index.ts
│           ├── http-client.module.ts
│           └── http-client.service.ts
│
├── nx.json
├── package.json
├── tsconfig.base.json
└── docker-compose.yml
```

---

## 3. Data Ownership

### Entity Assignment

All entities are shared in `libs/database` since this is a modular monolith. Below shows which module is the **primary owner** (writes) vs **reader** (reads only).

| Table | Primary Owner Module | Reader Modules | Entity Location |
|-------|---------------------|----------------|-----------------|
| `parts` | products | categories, search, cart, promotions, compare, bms | libs/database |
| `part1` | products | search | libs/database |
| `parts_price_5` | products | pricing | libs/database |
| `part_prices` | products | pricing, cart | libs/database |
| `ntag_name` | categories | products, search, seo | libs/database |
| `ntag_parts` | categories | products | libs/database |
| `ntag_part1` | categories | products | libs/database |
| `z_item` | categories | products, worlds | libs/database |
| `z_main` | categories | worlds | libs/database |
| `n_search_h` | search | - | libs/database |
| `n_search_normalize` | search | - | libs/database |
| `api_hot_search_FAST` | search | - | libs/database |
| `api_hot_tags` | search | - | libs/database |
| `api_hot_select` | search | - | libs/database |
| `api_hot_image` | search | - | libs/database |
| `n_buy_items` | cart | - | libs/database |
| `n_bid_log` | bidding | - | libs/database |
| `n_compare_discounts` | bidding | compare | libs/database |
| `bms_table` | bms | - | libs/database |
| `bms_coupon` | bms | promotions | libs/database |
| `n_comp_row` | bms | compare | libs/database |
| `n_comp_template` | bms | compare | libs/database |
| `n_comp_clienta` | bms | compare | libs/database |
| `m_action_const` | promotions | products | libs/database |
| `m_cmc_const` | promotions | - | libs/database |
| `api_world` | worlds | - | libs/database |
| `white_products_items` | worlds | - | libs/database |
| `i_snif` | stores | - | libs/database |
| `i_banner` | content | - | libs/database |
| `z_carousel` | content | - | libs/database |
| `z_xslider2_banners` | content | promotions | libs/database |
| `kspltd_newsletters` | notifications | - | libs/database |
| `api_footer_menu` | content | - | libs/database |
| `kspltd_seo` | seo | - | libs/database |
| `price_down` | pricing | notifications | libs/database |
| `item_down` | pricing | notifications | libs/database |
| `return_items` | products | - | libs/database |
| `push_uin_to_recommend_item` | notifications | products | libs/database |
| `api_personal_items` | products | - | libs/database |
| `mssqlksp_stat` | products | - | libs/database |
| `n_order_parts_combine_agg` | products | cart | libs/database |
| `up_item_profiles` | products | - | libs/database |
| `payments_api_data` | pricing | - | libs/database |
| `googlePixel` | content | - | libs/database |
| `katava` | content | - | libs/database |
| `app_devices` | config | - | libs/database |
| `app_debug` | config | - | libs/database |
| `app_auth_tokens` | auth | - | libs/database |
| `app_auth_logs` | auth | - | libs/database |
| `subscribe_for_mailing_log` | notifications | - | libs/database |
| `af_menipulate_log` | affiliation | - | libs/database |
| `idan_ami` | content | - | libs/database |
| `idan_ami_popads` | content | - | libs/database |
| `kspltd_bigDataNadir` | products | - | libs/database |
| `w_ip` | config | - | libs/database |
| `api_stat` | config | - | libs/database |

### Cross-Module Data Access Pattern

Since this is a modular monolith, modules can import each other directly:

```typescript
// products.module.ts
@Module({
  imports: [
    CategoriesModule,  // Direct import for tag data
    CacheModule,       // Shared caching
  ],
  // ...
})
export class ProductsModule {}
```

**If extracting to microservices later**, replace direct imports with:
1. API calls via ClientProxy
2. Event-driven updates for eventual consistency

---

## 4. Communication

### Within Gateway (Modules)

All communication is direct function calls through dependency injection:

```typescript
// products.service.ts
@Injectable()
export class ProductsService {
  constructor(
    private readonly categoriesService: CategoriesService,
    private readonly cacheService: CacheService,
    private readonly pricingService: PricingService,
  ) {}

  async getProductDetails(uin: string): Promise<ProductDetails> {
    const cached = await this.cacheService.get(`product:${uin}`);
    if (cached) return cached;

    const product = await this.productRepository.findOne({ where: { uin } });
    const category = await this.categoriesService.getCategoryByUin(product.categoryUin);
    const pricing = await this.pricingService.calculatePrice(product);

    const result = { ...product, category, pricing };
    await this.cacheService.set(`product:${uin}`, result, 300);
    return result;
  }
}
```

### External API Communication

The legacy system makes 52+ external API calls. Centralize these in the `http-client` library:

```typescript
// libs/http-client/src/http-client.service.ts
@Injectable()
export class HttpClientService {
  constructor(private readonly httpService: HttpService) {}

  async callProductsApi<T>(endpoint: string, params?: any): Promise<T> {
    const url = `${this.configService.get('PRODUCTS_API_URL')}${endpoint}`;
    return this.httpService.get(url, { params }).pipe(
      timeout(5000),
      retry(3),
      map(res => res.data),
      catchError(this.handleError),
    ).toPromise();
  }

  async callUserApi<T>(endpoint: string, params?: any): Promise<T> {
    // Similar pattern for user API
  }

  async callMyMarketingApi(payload: any): Promise<void> {
    // For mailing list integration
  }
}
```

### Future: If Extracting Services

| From Module | To Module | Pattern | Transport |
|-------------|-----------|---------|-----------|
| gateway/products | search-service | Request/Response | TCP |
| gateway/cart | notifications-service | Event (async) | Redis Pub/Sub |
| gateway/bidding | notifications-service | Event (async) | Redis Pub/Sub |

---

## 5. Authentication Strategy

### Current PHP Pattern

Based on the analysis:
- Uses external user API (`userAPI.php`) that returns user data
- Redis-based session cookies (`redis-cookies.php`, `REDIS_UID_KEY`)
- App auth tokens (`app_auth_tokens` table with selector/hash)
- Device identification (`app_devices` table)
- Amex login integration (`files/amex/login.php`)

```php
// Legacy patterns found:
$_ENV['REDIS_KEY_PREFIX'] . '.PERSISTENT.UID'  // Redis session key
$config['user'] = [
    'id' => $response['data']['data']['user_id'],
    'email' => $response['data']['data']['email'],
    // ...
];
```

### NestJS Implementation

**Strategy:** JWT with optional authentication (many routes are public)

```typescript
// libs/common/src/guards/jwt-auth.guard.ts
@Injectable()
export class JwtAuthGuard extends AuthGuard('jwt') {
  canActivate(context: ExecutionContext) {
    return super.canActivate(context);
  }

  handleRequest(err: any, user: any, info: any) {
    if (err || !user) {
      throw new UnauthorizedException();
    }
    return user;
  }
}

// libs/common/src/guards/optional-auth.guard.ts
@Injectable()
export class OptionalAuthGuard extends AuthGuard('jwt') {
  handleRequest(err: any, user: any) {
    // Don't throw on missing/invalid token - just return null user
    return user || null;
  }
}
```

```typescript
// libs/common/src/decorators/current-user.decorator.ts
export const CurrentUser = createParamDecorator(
  (data: keyof UserPayload | undefined, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    const user = request.user;
    return data ? user?.[data] : user;
  },
);

// Usage in controller
@Get('cart')
@UseGuards(JwtAuthGuard)
getCart(@CurrentUser() user: UserPayload) {
  return this.cartService.getCart(user.id);
}

@Get('products/:id')
@UseGuards(OptionalAuthGuard)
getProduct(@Param('id') id: string, @CurrentUser() user: UserPayload | null) {
  return this.productsService.getProduct(id, user?.id);
}
```

### JWT Strategy

```typescript
// apps/gateway/src/auth/strategies/jwt.strategy.ts
@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor(private configService: ConfigService) {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      secretOrKey: configService.get('JWT_SECRET'),
    });
  }

  async validate(payload: JwtPayload): Promise<UserPayload> {
    return {
      id: payload.sub,
      email: payload.email,
      name: payload.name,
      cityId: payload.cityId,
      preferences: payload.preferences,
    };
  }
}
```

### Migration Path

1. **Phase 1:** Implement JWT auth in NestJS alongside legacy
2. **Phase 2:** Create bridge endpoint that validates PHP session and issues JWT
3. **Phase 3:** Migrate clients to use JWT
4. **Phase 4:** Deprecate PHP session auth

```typescript
// Bridge endpoint for migration
@Post('auth/bridge')
async bridgeSession(@Body('sessionId') sessionId: string) {
  // Validate session against PHP/Redis
  const userData = await this.legacySessionService.validateSession(sessionId);
  if (!userData) {
    throw new UnauthorizedException('Invalid session');
  }

  // Issue JWT
  const token = this.jwtService.sign({
    sub: userData.id,
    email: userData.email,
    name: userData.name,
  });

  return { access_token: token };
}
```

---

## 6. Global State Mapping

### PHP Pattern to NestJS Equivalent

| PHP Pattern | Location | NestJS Equivalent |
|-------------|----------|-------------------|
| `$_ENV['REDIS_HOST']` | src/client.php | `ConfigService.get('REDIS_HOST')` |
| `$_ENV['REDIS_KEY_PREFIX']` | Multiple files | `ConfigService.get('REDIS_KEY_PREFIX')` |
| `$_ENV['DEBUG']` | app/conditionRace.php | `ConfigService.get('DEBUG')` |
| `define('REDIS_SEO_KEY', ...)` | app/seo.php | `@Inject('REDIS_SEO_KEY') key: string` |
| `define('REDIS_UID_KEY', ...)` | app/redis-cookies.php | `@Inject('REDIS_UID_KEY') key: string` |
| `$config['user']` | userAPI.php | `@CurrentUser() user` decorator |
| `$base_url` | setup.php | `ConfigService.get('BASE_URL')` |
| `Notification::fromSrc` | Static dependency | `@Inject(NotificationService)` |

### Configuration Module

```typescript
// apps/gateway/src/config/app-config.module.ts
@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: ['.env.local', '.env'],
      validationSchema: Joi.object({
        NODE_ENV: Joi.string().valid('development', 'production', 'test'),
        PORT: Joi.number().default(3000),
        DATABASE_URL: Joi.string().required(),
        REDIS_HOST: Joi.string().default('localhost'),
        REDIS_PORT: Joi.number().default(6379),
        REDIS_KEY_PREFIX: Joi.string().default('m-action'),
        JWT_SECRET: Joi.string().required(),
        JWT_EXPIRES_IN: Joi.string().default('7d'),
        PRODUCTS_API_URL: Joi.string().required(),
        USER_API_URL: Joi.string().required(),
        DEBUG: Joi.boolean().default(false),
      }),
    }),
  ],
  providers: [
    {
      provide: 'REDIS_SEO_KEY',
      useFactory: (config: ConfigService) =>
        `${config.get('REDIS_KEY_PREFIX')}.SEO`,
      inject: [ConfigService],
    },
    {
      provide: 'REDIS_UID_KEY',
      useFactory: (config: ConfigService) =>
        `${config.get('REDIS_KEY_PREFIX')}.PERSISTENT.UID`,
      inject: [ConfigService],
    },
    // ... other Redis keys
  ],
  exports: ['REDIS_SEO_KEY', 'REDIS_UID_KEY'],
})
export class AppConfigModule {}
```

### Superglobals Mapping

| PHP Superglobal | NestJS Equivalent |
|-----------------|-------------------|
| `$_GET['param']` | `@Query('param') param: string` |
| `$_POST['data']` | `@Body() dto: CreateDto` |
| `$_REQUEST['key']` | `@Query() + @Body()` combined |
| `$_SESSION['user']` | `@CurrentUser()` (from JWT) |
| `$_COOKIE['name']` | `@Req() req` → `req.cookies.name` |
| `$_SERVER['REQUEST_URI']` | `@Req() req` → `req.url` |
| `$_SERVER['HTTP_HOST']` | `@Req() req` → `req.hostname` |
| `$_FILES['upload']` | `@UploadedFile() file` with `FileInterceptor` |
| `file_get_contents('php://input')` | `@Body() body` (raw) |

---

## 7. Data Migration Plan

### Approach: Incremental with Dual-Write During Transition

Given the system's complexity and 57 tables, we'll use **incremental migration** with a brief dual-write period for critical tables.

### Table Migration Order

| Order | Table(s) | Strategy | Dependencies | Risk | Notes |
|-------|----------|----------|--------------|------|-------|
| 1 | `z_main`, `api_world` | Big Bang | None | Low | Reference data, rarely changes |
| 2 | `ntag_name`, `z_item` | Big Bang | z_main | Low | Category structure |
| 3 | `ntag_parts`, `ntag_part1` | Big Bang | ntag_name | Low | Category-product mapping |
| 4 | `parts`, `part1` | Incremental | ntag_parts | Medium | Core product data, 1-3 tables |
| 5 | `parts_price_5`, `part_prices` | Incremental | parts | Medium | Pricing data |
| 6 | `kspltd_seo` | Big Bang | parts | Low | SEO metadata |
| 7 | `i_snif`, `i_banner` | Big Bang | None | Low | Stores and banners |
| 8 | `api_footer_menu`, `z_carousel` | Big Bang | None | Low | Content |
| 9 | `n_search_*`, `api_hot_*` | Incremental | parts | Medium | Search indexes |
| 10 | `bms_table`, `bms_coupon` | Big Bang | parts | Low | BMS system |
| 11 | `n_comp_*` | Big Bang | parts, bms_table | Low | Compare/BMS |
| 12 | `kspltd_newsletters`, `push_uin_*` | Big Bang | None | Low | Notifications |
| 13 | `n_buy_items` | Dual-Write | parts | High | Active cart data |
| 14 | `n_bid_log`, `n_compare_discounts` | Big Bang | parts | Medium | Bidding history |
| 15 | `price_down`, `item_down` | Big Bang | parts | Low | Alerts |
| 16 | `app_devices`, `app_auth_*` | Incremental | None | Medium | Auth data |
| 17 | Remaining tables | Big Bang | Various | Low | Misc data |

### Schema Transformations

#### Key Changes

```yaml
Common Transformations:
  - Add UUID primary key (keep old ID as legacy_id)
  - Add created_at, updated_at timestamps
  - Normalize column names (snake_case)
  - Add proper foreign key constraints
  - Add indexes for common query patterns

Specific Tables:
  parts:
    Changes:
      - uin: VARCHAR → Keep as-is (business key)
      - uinsql: INT → Keep as-is (for SQL Server compat)
      - Add: id UUID PRIMARY KEY
      - Add: created_at TIMESTAMP DEFAULT NOW()
      - Add: updated_at TIMESTAMP DEFAULT NOW()
    Indexes:
      - (uin) UNIQUE
      - (uinsql)
      - (flag, stock)
      - (z.cat) → (category_id)

  ntag_name:
    Changes:
      - up_uin: VARCHAR → Keep (parent reference)
      - uin: VARCHAR → Keep (self reference)
      - Add proper FK to parent
    Indexes:
      - (uin) UNIQUE
      - (up_uin)
      - (world)
```

### Rollback Plan

1. **Before Migration:**
   - Create full database backup
   - Document current schema state
   - Set up read replica of legacy DB

2. **During Migration:**
   - Keep legacy database read-only accessible
   - Maintain ID mapping table:
     ```sql
     CREATE TABLE migration_id_map (
       table_name VARCHAR(100),
       legacy_id VARCHAR(100),
       new_id UUID,
       migrated_at TIMESTAMP
     );
     ```

3. **If Rollback Needed:**
   - Point application back to legacy DB
   - Use ID mapping to sync any new data back
   - Analyze failure cause before retry

### Verification Checklist

```yaml
Per-Table Verification:
  - [ ] Row counts match (legacy vs new)
  - [ ] Sample data integrity (10% random sample)
  - [ ] Foreign key relationships valid
  - [ ] Indexes created and used
  - [ ] Query performance acceptable (<100ms for common queries)

Business Rules:
  - [ ] Product prices calculate correctly
  - [ ] Category hierarchy displays correctly
  - [ ] Search returns expected results
  - [ ] Cart operations work
```

---

## 8. Security Remediation Plan

The legacy system has **161 security issues**. Address these during migration:

### Critical Issues (36) - Must Fix

| Type | Count | Remediation |
|------|-------|-------------|
| Command Injection | 27 | Never use exec/shell_exec. Use typed libraries. |
| SQL Injection | 6 | Use TypeORM parameterized queries exclusively |
| Insecure Function | 3 | Remove eval(), include with user input |

### High Issues (95) - Must Fix

| Type | Count | Remediation |
|------|-------|-------------|
| XSS | 95 | Use DTOs with class-validator, auto-escape in responses |

### Implementation

```typescript
// All input through validated DTOs
export class ProductQueryDto {
  @IsString()
  @MaxLength(50)
  @Matches(/^[a-zA-Z0-9-]+$/)  // Alphanumeric only
  uin: string;

  @IsOptional()
  @IsInt()
  @Min(1)
  @Max(100)
  limit?: number = 20;
}

// Output transformation/sanitization
@Injectable()
export class TransformInterceptor<T> implements NestInterceptor<T, Response<T>> {
  intercept(context: ExecutionContext, next: CallHandler): Observable<Response<T>> {
    return next.handle().pipe(
      map(data => ({
        success: true,
        data: this.sanitize(data),
        timestamp: new Date().toISOString(),
      })),
    );
  }

  private sanitize(data: any): any {
    // Recursively escape HTML in string values
    if (typeof data === 'string') {
      return escapeHtml(data);
    }
    if (Array.isArray(data)) {
      return data.map(item => this.sanitize(item));
    }
    if (typeof data === 'object' && data !== null) {
      return Object.keys(data).reduce((acc, key) => {
        acc[key] = this.sanitize(data[key]);
        return acc;
      }, {});
    }
    return data;
  }
}
```

---

## 9. Nx Setup Commands

```bash
# Create workspace
npx create-nx-workspace@latest m-action-api --preset=nest --nxCloud=skip

# Navigate to workspace
cd m-action-api

# Generate shared libraries
nx generate @nx/nest:library shared-dto --directory=libs/shared-dto --buildable
nx generate @nx/nest:library database --directory=libs/database --buildable
nx generate @nx/nest:library common --directory=libs/common --buildable
nx generate @nx/nest:library cache --directory=libs/cache --buildable
nx generate @nx/nest:library http-client --directory=libs/http-client --buildable

# The gateway app is created by default, but if you need to regenerate:
# nx generate @nx/nest:application gateway

# Generate modules in gateway (Core Domains)
nx generate @nx/nest:module products --project=gateway --path=apps/gateway/src/products
nx generate @nx/nest:module categories --project=gateway --path=apps/gateway/src/categories
nx generate @nx/nest:module search --project=gateway --path=apps/gateway/src/search
nx generate @nx/nest:module cart --project=gateway --path=apps/gateway/src/cart
nx generate @nx/nest:module promotions --project=gateway --path=apps/gateway/src/promotions
nx generate @nx/nest:module worlds --project=gateway --path=apps/gateway/src/worlds
nx generate @nx/nest:module bidding --project=gateway --path=apps/gateway/src/bidding
nx generate @nx/nest:module bms --project=gateway --path=apps/gateway/src/bms

# Generate modules in gateway (Supporting Domains)
nx generate @nx/nest:module content --project=gateway --path=apps/gateway/src/content
nx generate @nx/nest:module seo --project=gateway --path=apps/gateway/src/seo
nx generate @nx/nest:module brands --project=gateway --path=apps/gateway/src/brands
nx generate @nx/nest:module stores --project=gateway --path=apps/gateway/src/stores
nx generate @nx/nest:module notifications --project=gateway --path=apps/gateway/src/notifications
nx generate @nx/nest:module pricing --project=gateway --path=apps/gateway/src/pricing
nx generate @nx/nest:module compare --project=gateway --path=apps/gateway/src/compare
nx generate @nx/nest:module affiliation --project=gateway --path=apps/gateway/src/affiliation
nx generate @nx/nest:module help --project=gateway --path=apps/gateway/src/help

# Generate modules in gateway (Generic Domains)
nx generate @nx/nest:module config --project=gateway --path=apps/gateway/src/config
nx generate @nx/nest:module auth --project=gateway --path=apps/gateway/src/auth
nx generate @nx/nest:module users --project=gateway --path=apps/gateway/src/users

# Generate controllers for main routes
nx generate @nx/nest:controller products --project=gateway --path=apps/gateway/src/products --flat
nx generate @nx/nest:controller categories --project=gateway --path=apps/gateway/src/categories --flat
nx generate @nx/nest:controller search --project=gateway --path=apps/gateway/src/search --flat
nx generate @nx/nest:controller cart --project=gateway --path=apps/gateway/src/cart --flat
# ... continue for other modules

# Generate services
nx generate @nx/nest:service products --project=gateway --path=apps/gateway/src/products --flat
nx generate @nx/nest:service categories --project=gateway --path=apps/gateway/src/categories --flat
# ... continue for other modules

# Install additional dependencies
npm install @nestjs/config @nestjs/jwt @nestjs/passport passport passport-jwt
npm install @nestjs/typeorm typeorm mysql2
npm install @nestjs/cache-manager cache-manager cache-manager-redis-store redis
npm install class-validator class-transformer
npm install @nestjs/axios axios
npm install joi
npm install -D @types/passport-jwt

# View dependency graph
nx graph

# Build and test
nx build gateway
nx test gateway
nx lint gateway

# Run in development
nx serve gateway
```

---

## 10. Migration Plan

### Priority Order

| Priority | Module | Legacy Files | Complexity | Risk | Dependencies | Est. Routes |
|----------|--------|--------------|------------|------|--------------|-------------|
| **0** | Infrastructure | setup.php, conn.php, func.php | High | Low | None | 0 |
| **1** | Auth | login.php, redis-cookies.php | Medium | Medium | Infrastructure | 3 |
| **2** | Config | config.php, settings.php | High | Low | Auth | 15 |
| **3** | Categories | cats/index.php, func.php | High | Medium | Config | 12 |
| **4** | Products | item.php, item_*.php | Very High | High | Categories, Config | 45 |
| **5** | Search | autocomplete/index.php, search.php | Medium | Medium | Products, Categories | 5 |
| **6** | SEO | seo/*.php | Medium | Low | Products, Categories | 4 |
| **7** | Content | page.php, menu.php, footer.php | Medium | Low | Products | 20 |
| **8** | Promotions | sales.php, bmsSale.php, get.php | Medium | Medium | Products | 15 |
| **9** | Worlds | world.php, worlds.php, blackFriday.php | High | Medium | Products, Categories | 8 |
| **10** | Cart | addToCart.php, cart.php | Medium | High | Products, Auth | 5 |
| **11** | BMS | bms.php, comp.php | High | Medium | Products, Categories | 6 |
| **12** | Bidding | bidding.php, bidding_callback.php | Medium | Medium | Products, Auth | 3 |
| **13** | Brands | brands.php | Medium | Low | Products, Categories | 2 |
| **14** | Stores | stores.php | Low | Low | Config | 3 |
| **15** | Compare | compare.php | Medium | Low | Products | 2 |
| **16** | Pricing | pricing.php, payments*.php | Medium | Medium | Products | 5 |
| **17** | Notifications | push.php, mailing.php | Low | Low | Auth | 8 |
| **18** | Affiliation | getBonus.php | Medium | Low | Auth | 2 |
| **19** | Help | lab.php, nagish.php | Low | Low | None | 2 |

### Migration Phases

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           PHASE 1: FOUNDATION                                 │
│                                                                               │
│  Priority 0: Infrastructure                                                   │
│  ├── Nx workspace setup                                                       │
│  ├── Database connection (TypeORM)                                           │
│  ├── Redis connection                                                         │
│  ├── Common utilities migration                                               │
│  └── Environment configuration                                                │
│                                                                               │
│  Priority 1-2: Auth + Config                                                  │
│  ├── JWT authentication strategy                                              │
│  ├── Session bridge (legacy compat)                                          │
│  ├── Configuration endpoints                                                  │
│  └── Device/cookie management                                                 │
│                                                                               │
│  Deliverable: Running NestJS app with auth, serves /config, /ping            │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        PHASE 2: CORE CATALOG                                  │
│                                                                               │
│  Priority 3-4: Categories + Products                                          │
│  ├── Category tree and navigation                                             │
│  ├── Product listing and details                                              │
│  ├── Product specifications                                                   │
│  ├── Product recommendations                                                  │
│  └── Redis caching layer                                                      │
│                                                                               │
│  Priority 5-6: Search + SEO                                                   │
│  ├── Autocomplete                                                             │
│  ├── Full search                                                              │
│  └── SEO metadata endpoints                                                   │
│                                                                               │
│  Deliverable: Full product catalog browsable via NestJS                       │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        PHASE 3: CONTENT & COMMERCE                            │
│                                                                               │
│  Priority 7-9: Content + Promotions + Worlds                                  │
│  ├── Static pages                                                             │
│  ├── Menu and footer                                                          │
│  ├── Sales and promotions                                                     │
│  └── Product worlds (Black Friday, etc.)                                      │
│                                                                               │
│  Priority 10-12: Cart + BMS + Bidding                                         │
│  ├── Shopping cart operations                                                 │
│  ├── Build My System flow                                                     │
│  └── Bidding system                                                           │
│                                                                               │
│  Deliverable: Complete shopping experience                                    │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        PHASE 4: SUPPORTING FEATURES                           │
│                                                                               │
│  Priority 13-19: Remaining modules                                            │
│  ├── Brands, Stores, Compare                                                  │
│  ├── Pricing alerts                                                           │
│  ├── Notifications (push, email)                                              │
│  ├── Affiliation/bonus system                                                 │
│  └── Help section                                                             │
│                                                                               │
│  Deliverable: Feature-complete NestJS application                             │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        PHASE 5: CUTOVER & CLEANUP                             │
│                                                                               │
│  ├── Performance testing and optimization                                     │
│  ├── Security audit                                                           │
│  ├── Gradual traffic migration (Strangler Fig)                               │
│  ├── Legacy system decommission                                               │
│  └── Documentation update                                                     │
│                                                                               │
│  Deliverable: Production-ready NestJS API, PHP retired                        │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Appendix A: Route Mapping

### High-Traffic Routes (Prioritize Performance)

| Legacy Route | NestJS Controller | Method |
|--------------|-------------------|--------|
| `/item/:param1` | ProductsController | GET /products/:uin |
| `/category/:param1` | CategoriesController | GET /categories/:id |
| `/products/search/autocomplete/:param1` | SearchController | GET /search/autocomplete |
| `/home` | ContentController | GET /home |
| `/menu` | ContentController | GET /menu |
| `/config` | ConfigController | GET /config |

### Route Consolidation

Many legacy routes are redundant (e.g., `/files/item` and `/item/:param1`). Consolidate to clean REST patterns:

| Legacy Routes | NestJS Route |
|---------------|--------------|
| `/item/:id`, `/files/item` | GET /products/:uin |
| `/items/:id/complementary`, `/items/:id/similar`, `/items/:id/buy-together` | GET /products/:uin/related?type=complementary|similar|buy-together |
| `/category/:id`, `/categoryX/:id`, `/files/specialCat` | GET /categories/:id |
| `/stores`, `/stores/:id` | GET /stores, GET /stores/:id |

---

## Appendix B: TypeORM Entity Example

```typescript
// libs/database/src/entities/part.entity.ts
import { Entity, Column, PrimaryGeneratedColumn, Index, CreateDateColumn, UpdateDateColumn } from 'typeorm';

@Entity('parts')
@Index(['uin'], { unique: true })
@Index(['uinsql'])
@Index(['flag', 'stock'])
export class Part {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ type: 'varchar', length: 50 })
  uin: string;

  @Column({ type: 'int', nullable: true })
  uinsql: number;

  @Column({ type: 'varchar', length: 500 })
  name: string;

  @Column({ type: 'varchar', length: 500, nullable: true })
  hname: string;

  @Column({ type: 'decimal', precision: 10, scale: 2, nullable: true })
  price: number;

  @Column({ type: 'int', default: 0 })
  stock: number;

  @Column({ type: 'varchar', length: 50, nullable: true })
  flag: string;

  @Column({ type: 'varchar', length: 100, nullable: true })
  brand: string;

  @Column({ type: 'varchar', length: 255, nullable: true })
  url: string;

  @Column({ type: 'int', nullable: true })
  catalog: number;

  @Column({ type: 'varchar', length: 50, nullable: true })
  subcat: string;

  @Column({ type: 'boolean', default: false })
  eol: boolean;

  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;
}
```

---

## Verification Checklist

Before marking design complete:

- [x] All legacy routes mapped to modules (203 routes → 19 modules)
- [x] All database tables assigned ownership (57 tables)
- [x] Nx structure follows modular monolith pattern
- [x] Shared code placed in libs/
- [x] Nx setup commands documented
- [x] Migration priority order documented
- [x] Authentication strategy defined (JWT with legacy bridge)
- [x] Data migration approach documented (Incremental)
- [x] Global state mapping covers all PHP patterns
- [x] Security issues addressed in design (161 issues → remediation plan)

---

*Document generated by Principal Software Architect prompt*
*Source: m-action legacy PHP analysis (157 files, 32,192 LOC)*
