#!/bin/bash
# create_nx_workspace.sh
# Automatically creates an Nx monorepo with NestJS for the migrated project
#
# Usage:
#   ./scripts/create_nx_workspace.sh -o ./output -n my-project
#   ./scripts/create_nx_workspace.sh -o ./output  # Uses source project name

set -e
set -o pipefail  # Ensure pipeline failures are caught

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Nx version to use (tested and stable with Node.js 18-22)
# Node.js 25 has compatibility issues with create-nx-workspace, so we use manual setup
NX_VERSION="22.3.3"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLKIT_ROOT="$(dirname "$SCRIPT_DIR")"

usage() {
    cat << EOF
${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}
${GREEN}  Nx Workspace Generator${NC}
${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}

Creates an Nx monorepo with NestJS based on migration analysis.

${YELLOW}Usage:${NC}
  $0 -o <output_dir> [options]

${YELLOW}Required:${NC}
  -o, --output <dir>     Migration output directory (contains analysis/)

${YELLOW}Options:${NC}
  -n, --name <name>      Project name (default: derived from source project)
  -t, --target <dir>     Target directory for Nx workspace (default: same level as source)
  --skip-install         Skip npm install (faster, but requires manual install)
  --dry-run              Show what would be created without executing
  -h, --help             Show this help

${YELLOW}Example:${NC}
  $0 -o ./output -n my-ecommerce-api
  $0 -o ./output --target /path/to/workspace

${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}
EOF
    exit 0
}

# Default values
OUTPUT_DIR=""
PROJECT_NAME=""
TARGET_DIR=""
SKIP_INSTALL=false
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -n|--name)
            PROJECT_NAME="$2"
            shift 2
            ;;
        -t|--target)
            TARGET_DIR="$2"
            shift 2
            ;;
        --skip-install)
            SKIP_INSTALL=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            usage
            ;;
    esac
done

# Validate required arguments
if [ -z "$OUTPUT_DIR" ]; then
    echo -e "${RED}Error: --output is required${NC}"
    usage
fi

if [ ! -d "$OUTPUT_DIR" ]; then
    echo -e "${RED}Error: Output directory does not exist: $OUTPUT_DIR${NC}"
    exit 1
fi

# Resolve output directory to absolute path
OUTPUT_DIR=$(cd "$OUTPUT_DIR" && pwd)

# Check for required analysis files
if [ ! -f "$OUTPUT_DIR/analysis/legacy_analysis.json" ]; then
    echo -e "${RED}Error: No legacy_analysis.json found. Run master_migration.sh first.${NC}"
    exit 1
fi

# Load source project info
SOURCE_PROJECT=""
if [ -f "$OUTPUT_DIR/analysis/extracted_services.json" ]; then
    SOURCE_PROJECT=$(python3 -c "import json; print(json.load(open('$OUTPUT_DIR/analysis/extracted_services.json')).get('source_project', ''))" 2>/dev/null || echo "")
fi

if [ -z "$SOURCE_PROJECT" ] && [ -f "$OUTPUT_DIR/analysis/discovered_configs.json" ]; then
    # Try to get from discovered_configs (would need to add this field)
    SOURCE_PROJECT=$(dirname "$OUTPUT_DIR")
fi

# Derive project name if not provided
if [ -z "$PROJECT_NAME" ]; then
    if [ -n "$SOURCE_PROJECT" ]; then
        PROJECT_NAME=$(basename "$SOURCE_PROJECT" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//' | sed 's/-$//')
        PROJECT_NAME="${PROJECT_NAME}-api"
    else
        PROJECT_NAME="migrated-api"
    fi
fi

# Determine target directory
if [ -z "$TARGET_DIR" ]; then
    if [ -n "$SOURCE_PROJECT" ] && [ -d "$SOURCE_PROJECT" ]; then
        TARGET_DIR="$(dirname "$SOURCE_PROJECT")/$PROJECT_NAME"
    else
        TARGET_DIR="$(dirname "$OUTPUT_DIR")/$PROJECT_NAME"
    fi
fi

# Banner
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  ${GREEN}Nx Workspace Generator${NC}                                                  ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Create NestJS monorepo from migration analysis                           ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Analysis:${NC}     $OUTPUT_DIR"
echo -e "${BLUE}Project Name:${NC} $PROJECT_NAME"
echo -e "${BLUE}Target:${NC}       $TARGET_DIR"
echo -e "${BLUE}Nx Version:${NC}   $NX_VERSION"
echo -e "${BLUE}Skip Install:${NC} $SKIP_INSTALL"
echo ""

# Check if target already exists
if [ -d "$TARGET_DIR" ]; then
    echo -e "${RED}Error: Target directory already exists: $TARGET_DIR${NC}"
    echo -e "${YELLOW}Remove it first or choose a different name with --name${NC}"
    exit 1
fi

# Check prerequisites
echo -e "${CYAN}Checking prerequisites...${NC}"

if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is required but not installed${NC}"
    exit 1
fi
NODE_VERSION=$(node --version)
echo -e "  ${GREEN}✓${NC} Node.js: $NODE_VERSION"

if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm is required but not installed${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} npm: $(npm --version)"

# Check for npx
if ! command -v npx &> /dev/null; then
    echo -e "${RED}Error: npx is required but not installed${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} npx: available"

# Check for python3 (needed for entity index generation)
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not installed${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} Python: $(python3 --version 2>&1 | cut -d' ' -f2)"

echo ""

# Load extracted services
SERVICES=()
TRANSPORT="tcp"
if [ -f "$OUTPUT_DIR/analysis/extracted_services.json" ]; then
    TRANSPORT=$(python3 -c "import json; print(json.load(open('$OUTPUT_DIR/analysis/extracted_services.json')).get('transport', 'tcp'))" 2>/dev/null || echo "tcp")
    while IFS= read -r service; do
        [ -n "$service" ] && SERVICES+=("$service")
    done < <(python3 -c "import json; [print(s['service_name']) for s in json.load(open('$OUTPUT_DIR/analysis/extracted_services.json')).get('services', [])]" 2>/dev/null)
fi

echo -e "${BLUE}Services to create:${NC}"
echo -e "  • gateway (main HTTP API)"
for svc in "${SERVICES[@]}"; do
    echo -e "  • $svc (microservice)"
done
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY RUN - Would create:${NC}"
    echo "  Workspace: $TARGET_DIR"
    echo "  Apps: gateway, ${SERVICES[*]}"
    echo "  Libs: shared-dto, database, common, contracts/*"
    exit 0
fi

# ═══════════════════════════════════════════════════════════════════════════
# Step 1: Create Nx Workspace (Manual Setup for Node.js 25+ compatibility)
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Step 1: Creating Nx Workspace${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Create parent directory if needed
mkdir -p "$(dirname "$TARGET_DIR")"

echo -e "  ${CYAN}Creating Nx workspace with NestJS preset (v$NX_VERSION)...${NC}"
echo -e "  ${YELLOW}This may take a few minutes...${NC}"
echo ""

# Check Node.js version for compatibility
NODE_MAJOR_VERSION=$(node --version | sed 's/v\([0-9]*\).*/\1/')

# Manual workspace setup (works with Node.js 25+)
# This bypasses the create-nx-workspace CLI which has compatibility issues

mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

# Create package.json
cat > package.json << PKGJSON
{
  "name": "@${PROJECT_NAME}/source",
  "version": "0.0.0",
  "private": true,
  "scripts": {
    "start": "nx serve",
    "build": "nx build",
    "test": "nx test"
  },
  "devDependencies": {
    "@nx/eslint": "^${NX_VERSION}",
    "@nx/eslint-plugin": "^${NX_VERSION}",
    "@nx/jest": "^${NX_VERSION}",
    "@nx/js": "^${NX_VERSION}",
    "@nx/nest": "^${NX_VERSION}",
    "@nx/node": "^${NX_VERSION}",
    "@nx/webpack": "^${NX_VERSION}",
    "@nx/workspace": "^${NX_VERSION}",
    "@swc-node/register": "~1.10.9",
    "@swc/core": "~1.7.26",
    "@swc/helpers": "~0.5.12",
    "@types/jest": "^29.5.12",
    "@types/node": "~18.16.9",
    "@typescript-eslint/eslint-plugin": "^8.0.0",
    "@typescript-eslint/parser": "^8.0.0",
    "eslint": "^9.8.0",
    "typescript-eslint": "^8.0.0",
    "eslint-config-prettier": "^9.0.0",
    "jest": "^29.7.0",
    "jest-environment-node": "^29.7.0",
    "nx": "^${NX_VERSION}",
    "prettier": "^3.0.0",
    "ts-jest": "^29.1.0",
    "ts-node": "10.9.1",
    "typescript": "~5.6.2"
  },
  "dependencies": {
    "@nestjs/common": "^10.0.0",
    "@nestjs/core": "^10.0.0",
    "@nestjs/platform-express": "^10.0.0",
    "axios": "^1.6.0",
    "reflect-metadata": "^0.2.0",
    "rxjs": "^7.8.0",
    "tslib": "^2.3.0"
  }
}
PKGJSON

# Create nx.json
cat > nx.json << NXJSON
{
  "\$schema": "./node_modules/nx/schemas/nx-schema.json",
  "defaultBase": "main",
  "namedInputs": {
    "default": ["{projectRoot}/**/*", "sharedGlobals"],
    "production": [
      "default",
      "!{projectRoot}/**/?(*.)+(spec|test).[jt]s?(x)?(.snap)",
      "!{projectRoot}/tsconfig.spec.json",
      "!{projectRoot}/jest.config.[jt]s",
      "!{projectRoot}/src/test-setup.[jt]s",
      "!{projectRoot}/test-setup.[jt]s"
    ],
    "sharedGlobals": []
  },
  "plugins": [
    {
      "plugin": "@nx/eslint/plugin",
      "options": {
        "targetName": "lint"
      }
    },
    {
      "plugin": "@nx/jest/plugin",
      "options": {
        "targetName": "test"
      }
    }
  ],
  "targetDefaults": {
    "build": {
      "cache": true,
      "dependsOn": ["^build"],
      "inputs": ["production", "^production"]
    },
    "lint": {
      "cache": true
    },
    "test": {
      "cache": true
    }
  },
  "nxCloudAccessToken": ""
}
NXJSON

# Create tsconfig.base.json
cat > tsconfig.base.json << TSBASE
{
  "compileOnSave": false,
  "compilerOptions": {
    "rootDir": ".",
    "sourceMap": true,
    "declaration": false,
    "moduleResolution": "node",
    "emitDecoratorMetadata": true,
    "experimentalDecorators": true,
    "importHelpers": true,
    "target": "es2015",
    "module": "esnext",
    "lib": ["es2020", "dom"],
    "skipLibCheck": true,
    "skipDefaultLibCheck": true,
    "baseUrl": ".",
    "paths": {}
  },
  "exclude": ["node_modules", "tmp"]
}
TSBASE

# Create .prettierrc
cat > .prettierrc << PRETRC
{
  "singleQuote": true
}
PRETRC

# Create .prettierignore
cat > .prettierignore << PRETIG
/dist
/coverage
PRETIG

# Create .gitignore
cat > .gitignore << GITIG
# Dependencies
node_modules

# Build
dist
tmp
out-tsc

# IDE
.idea
.vscode
*.swp
*.swo

# Debug
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# OS
.DS_Store
Thumbs.db

# Nx
.nx/cache
.nx/workspace-data

# Environment files
.env
.env.local
GITIG

# Create .editorconfig
cat > .editorconfig << EDITCFG
root = true

[*]
charset = utf-8
indent_style = space
indent_size = 2
insert_final_newline = true
trim_trailing_whitespace = true

[*.md]
max_line_length = off
trim_trailing_whitespace = false
EDITCFG

# Create jest.preset.js
cat > jest.preset.js << JESTPRESET
const nxPreset = require('@nx/jest/preset').default;

module.exports = { ...nxPreset };
JESTPRESET

# Create jest.config.ts
cat > jest.config.ts << JESTCFG
import { getJestProjectsAsync } from '@nx/jest';

export default async () => ({
  projects: await getJestProjectsAsync(),
});
JESTCFG

# Create eslint.config.js
cat > eslint.config.js << ESLINTCFG
const nx = require('@nx/eslint-plugin');

module.exports = [
  ...nx.configs['flat/base'],
  ...nx.configs['flat/typescript'],
  ...nx.configs['flat/javascript'],
  {
    ignores: ['**/dist'],
  },
  {
    files: ['**/*.ts', '**/*.tsx', '**/*.js', '**/*.jsx'],
    rules: {
      '@nx/enforce-module-boundaries': [
        'error',
        {
          enforceBuildableLibDependency: true,
          allow: ['^.*/eslint(\\.base)?\\.config\\.[cm]?js$'],
          depConstraints: [
            {
              sourceTag: '*',
              onlyDependOnLibsWithTags: ['*'],
            },
          ],
        },
      ],
    },
  },
  {
    files: ['**/*.ts', '**/*.tsx', '**/*.js', '**/*.jsx'],
    rules: {},
  },
];
ESLINTCFG

# Create apps directory structure
mkdir -p apps/gateway/src/app

# Create gateway project.json
cat > apps/gateway/project.json << GWPROJ
{
  "name": "gateway",
  "\$schema": "../../node_modules/nx/schemas/project-schema.json",
  "sourceRoot": "apps/gateway/src",
  "projectType": "application",
  "tags": [],
  "targets": {
    "build": {
      "executor": "@nx/webpack:webpack",
      "outputs": ["{options.outputPath}"],
      "defaultConfiguration": "production",
      "options": {
        "target": "node",
        "compiler": "tsc",
        "outputPath": "dist/apps/gateway",
        "main": "apps/gateway/src/main.ts",
        "tsConfig": "apps/gateway/tsconfig.app.json",
        "assets": [],
        "webpackConfig": "apps/gateway/webpack.config.js",
        "generatePackageJson": true
      },
      "configurations": {
        "development": {},
        "production": {}
      }
    },
    "serve": {
      "executor": "@nx/js:node",
      "defaultConfiguration": "development",
      "options": {
        "buildTarget": "gateway:build"
      },
      "configurations": {
        "development": {
          "buildTarget": "gateway:build:development"
        },
        "production": {
          "buildTarget": "gateway:build:production"
        }
      }
    }
  }
}
GWPROJ

# Create gateway tsconfig.json
cat > apps/gateway/tsconfig.json << GWTS
{
  "extends": "../../tsconfig.base.json",
  "files": [],
  "include": [],
  "references": [
    {
      "path": "./tsconfig.app.json"
    },
    {
      "path": "./tsconfig.spec.json"
    }
  ],
  "compilerOptions": {
    "esModuleInterop": true
  }
}
GWTS

# Create gateway tsconfig.app.json
cat > apps/gateway/tsconfig.app.json << GWTSAPP
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "outDir": "../../dist/out-tsc",
    "module": "commonjs",
    "types": ["node"],
    "emitDecoratorMetadata": true,
    "target": "es2021"
  },
  "exclude": ["jest.config.ts", "src/**/*.spec.ts", "src/**/*.test.ts"],
  "include": ["src/**/*.ts"]
}
GWTSAPP

# Create gateway tsconfig.spec.json
cat > apps/gateway/tsconfig.spec.json << GWTSSPEC
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "outDir": "../../dist/out-tsc",
    "module": "commonjs",
    "types": ["jest", "node"]
  },
  "include": [
    "jest.config.ts",
    "src/**/*.test.ts",
    "src/**/*.spec.ts",
    "src/**/*.d.ts"
  ]
}
GWTSSPEC

# Create gateway jest.config.ts
cat > apps/gateway/jest.config.ts << GWJEST
export default {
  displayName: 'gateway',
  preset: '../../jest.preset.js',
  testEnvironment: 'node',
  transform: {
    '^.+\\.[tj]s$': ['ts-jest', { tsconfig: '<rootDir>/tsconfig.spec.json' }],
  },
  moduleFileExtensions: ['ts', 'js', 'html'],
  coverageDirectory: '../../coverage/apps/gateway',
};
GWJEST

# Create gateway webpack.config.js
cat > apps/gateway/webpack.config.js << GWWEBPACK
const { NxAppWebpackPlugin } = require('@nx/webpack/app-plugin');
const { join } = require('path');

module.exports = {
  output: {
    path: join(__dirname, '../../dist/apps/gateway'),
  },
  plugins: [
    new NxAppWebpackPlugin({
      target: 'node',
      compiler: 'tsc',
      main: './src/main.ts',
      tsConfig: './tsconfig.app.json',
      assets: [],
      optimization: false,
      outputHashing: 'none',
      generatePackageJson: true,
    }),
  ],
};
GWWEBPACK

# Create gateway source files
mkdir -p apps/gateway/src/assets

cat > apps/gateway/src/main.ts << GWMAIN
import { Logger } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app/app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  const globalPrefix = 'api';
  app.setGlobalPrefix(globalPrefix);
  const port = process.env.PORT || 3000;
  await app.listen(port);
  Logger.log(\`🚀 Application is running on: http://localhost:\${port}/\${globalPrefix}\`);
}

bootstrap();
GWMAIN

cat > apps/gateway/src/app/app.module.ts << GWAPPMOD
import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';

@Module({
  imports: [],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
GWAPPMOD

cat > apps/gateway/src/app/app.controller.ts << GWCTRL
import { Controller, Get } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get()
  getData() {
    return this.appService.getData();
  }
}
GWCTRL

cat > apps/gateway/src/app/app.service.ts << GWSVC
import { Injectable } from '@nestjs/common';

@Injectable()
export class AppService {
  getData(): { message: string } {
    return { message: 'Hello API' };
  }
}
GWSVC

cat > apps/gateway/src/app/app.controller.spec.ts << GWSPEC
import { Test, TestingModule } from '@nestjs/testing';
import { AppController } from './app.controller';
import { AppService } from './app.service';

describe('AppController', () => {
  let app: TestingModule;

  beforeAll(async () => {
    app = await Test.createTestingModule({
      controllers: [AppController],
      providers: [AppService],
    }).compile();
  });

  describe('getData', () => {
    it('should return "Hello API"', () => {
      const appController = app.get<AppController>(AppController);
      expect(appController.getData()).toEqual({ message: 'Hello API' });
    });
  });
});
GWSPEC

# Create .vscode directory with settings
mkdir -p .vscode
cat > .vscode/extensions.json << VSCEXT
{
  "recommendations": ["nrwl.angular-console", "esbenp.prettier-vscode", "dbaeumer.vscode-eslint"]
}
VSCEXT

# Create libs directory
mkdir -p libs

echo -e "  ${CYAN}Installing npm dependencies...${NC}"
echo -e "  ${YELLOW}This may take a few minutes...${NC}"

# Install dependencies
npm install --legacy-peer-deps 2>&1 | grep -E "(added|npm warn|npm error)" || true

echo ""
echo -e "  ${GREEN}✓${NC} Nx workspace created"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# Step 2: Create Shared Libraries (Manual Setup)
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Step 2: Creating Shared Libraries${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Function to create a NestJS library manually
create_nestjs_lib() {
    local LIB_NAME="$1"
    local LIB_DIR="libs/$LIB_NAME"

    echo -e "  ${CYAN}Creating $LIB_NAME library...${NC}"

    mkdir -p "$LIB_DIR/src/lib"

    # Create project.json
    cat > "$LIB_DIR/project.json" << LIBPROJ
{
  "name": "$LIB_NAME",
  "\$schema": "../../node_modules/nx/schemas/project-schema.json",
  "sourceRoot": "$LIB_DIR/src",
  "projectType": "library",
  "tags": [],
  "targets": {
    "build": {
      "executor": "@nx/js:tsc",
      "outputs": ["{options.outputPath}"],
      "options": {
        "outputPath": "dist/$LIB_DIR",
        "main": "$LIB_DIR/src/index.ts",
        "tsConfig": "$LIB_DIR/tsconfig.lib.json",
        "assets": []
      }
    }
  }
}
LIBPROJ

    # Create tsconfig.json
    cat > "$LIB_DIR/tsconfig.json" << LIBTS
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "module": "commonjs",
    "forceConsistentCasingInFileNames": true,
    "strict": true,
    "noImplicitOverride": true,
    "noPropertyAccessFromIndexSignature": false,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  },
  "files": [],
  "include": [],
  "references": [
    {
      "path": "./tsconfig.lib.json"
    },
    {
      "path": "./tsconfig.spec.json"
    }
  ]
}
LIBTS

    # Create tsconfig.lib.json
    cat > "$LIB_DIR/tsconfig.lib.json" << LIBTSLIB
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "outDir": "../../dist/out-tsc",
    "declaration": true,
    "types": ["node"]
  },
  "include": ["src/**/*.ts"],
  "exclude": ["jest.config.ts", "src/**/*.spec.ts", "src/**/*.test.ts"]
}
LIBTSLIB

    # Create tsconfig.spec.json
    cat > "$LIB_DIR/tsconfig.spec.json" << LIBTSSPEC
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "outDir": "../../dist/out-tsc",
    "module": "commonjs",
    "types": ["jest", "node"]
  },
  "include": [
    "jest.config.ts",
    "src/**/*.test.ts",
    "src/**/*.spec.ts",
    "src/**/*.d.ts"
  ]
}
LIBTSSPEC

    # Create jest.config.ts
    cat > "$LIB_DIR/jest.config.ts" << LIBJEST
export default {
  displayName: '$LIB_NAME',
  preset: '../../jest.preset.js',
  testEnvironment: 'node',
  transform: {
    '^.+\\.[tj]s$': ['ts-jest', { tsconfig: '<rootDir>/tsconfig.spec.json' }],
  },
  moduleFileExtensions: ['ts', 'js', 'html'],
  coverageDirectory: '../../coverage/$LIB_DIR',
};
LIBJEST

    # Create module file
    local MODULE_CLASS=$(echo "$LIB_NAME" | sed 's/-\([a-z]\)/\U\1/g' | sed 's/^\([a-z]\)/\U\1/')

    cat > "$LIB_DIR/src/lib/${LIB_NAME}.module.ts" << LIBMOD
import { Module } from '@nestjs/common';

@Module({
  controllers: [],
  providers: [],
  exports: [],
})
export class ${MODULE_CLASS}Module {}
LIBMOD

    # Create index.ts
    cat > "$LIB_DIR/src/index.ts" << LIBIDX
export * from './lib/${LIB_NAME}.module';
LIBIDX
}

# Create the libraries
create_nestjs_lib "shared-dto"
create_nestjs_lib "database"
create_nestjs_lib "common"

# Update tsconfig.base.json with path mappings
python3 -c "
import json
with open('tsconfig.base.json', 'r') as f:
    config = json.load(f)
config['compilerOptions']['paths'] = {
    '@${PROJECT_NAME}/shared-dto': ['libs/shared-dto/src/index.ts'],
    '@${PROJECT_NAME}/database': ['libs/database/src/index.ts'],
    '@${PROJECT_NAME}/common': ['libs/common/src/index.ts']
}
with open('tsconfig.base.json', 'w') as f:
    json.dump(config, f, indent=2)
"

echo ""
echo -e "  ${GREEN}✓${NC} Shared libraries created"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# Step 3: Create Microservice Apps (Manual Setup)
# ═══════════════════════════════════════════════════════════════════════════
if [ ${#SERVICES[@]} -gt 0 ]; then
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Step 3: Creating Microservice Apps${NC}"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Function to create a NestJS microservice app manually
    create_nestjs_app() {
        local APP_NAME="$1"
        local APP_DIR="apps/$APP_NAME"
        local APP_PORT="$2"

        echo -e "  ${CYAN}Creating $APP_NAME microservice...${NC}"

        mkdir -p "$APP_DIR/src/app"
        mkdir -p "$APP_DIR/src/assets"

        # Create project.json
        cat > "$APP_DIR/project.json" << APPPROJ
{
  "name": "$APP_NAME",
  "\$schema": "../../node_modules/nx/schemas/project-schema.json",
  "sourceRoot": "$APP_DIR/src",
  "projectType": "application",
  "tags": ["type:microservice"],
  "targets": {
    "build": {
      "executor": "@nx/webpack:webpack",
      "outputs": ["{options.outputPath}"],
      "defaultConfiguration": "production",
      "options": {
        "target": "node",
        "compiler": "tsc",
        "outputPath": "dist/$APP_DIR",
        "main": "$APP_DIR/src/main.ts",
        "tsConfig": "$APP_DIR/tsconfig.app.json",
        "assets": [],
        "webpackConfig": "$APP_DIR/webpack.config.js",
        "generatePackageJson": true
      },
      "configurations": {
        "development": {},
        "production": {}
      }
    },
    "serve": {
      "executor": "@nx/js:node",
      "defaultConfiguration": "development",
      "options": {
        "buildTarget": "$APP_NAME:build"
      },
      "configurations": {
        "development": {
          "buildTarget": "$APP_NAME:build:development"
        },
        "production": {
          "buildTarget": "$APP_NAME:build:production"
        }
      }
    }
  }
}
APPPROJ

        # Create tsconfig.json
        cat > "$APP_DIR/tsconfig.json" << APPTS
{
  "extends": "../../tsconfig.base.json",
  "files": [],
  "include": [],
  "references": [
    {
      "path": "./tsconfig.app.json"
    },
    {
      "path": "./tsconfig.spec.json"
    }
  ],
  "compilerOptions": {
    "esModuleInterop": true
  }
}
APPTS

        # Create tsconfig.app.json
        cat > "$APP_DIR/tsconfig.app.json" << APPTSAPP
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "outDir": "../../dist/out-tsc",
    "module": "commonjs",
    "types": ["node"],
    "emitDecoratorMetadata": true,
    "target": "es2021"
  },
  "exclude": ["jest.config.ts", "src/**/*.spec.ts", "src/**/*.test.ts"],
  "include": ["src/**/*.ts"]
}
APPTSAPP

        # Create tsconfig.spec.json
        cat > "$APP_DIR/tsconfig.spec.json" << APPTSSPEC
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "outDir": "../../dist/out-tsc",
    "module": "commonjs",
    "types": ["jest", "node"]
  },
  "include": [
    "jest.config.ts",
    "src/**/*.test.ts",
    "src/**/*.spec.ts",
    "src/**/*.d.ts"
  ]
}
APPTSSPEC

        # Create jest.config.ts
        cat > "$APP_DIR/jest.config.ts" << APPJEST
export default {
  displayName: '$APP_NAME',
  preset: '../../jest.preset.js',
  testEnvironment: 'node',
  transform: {
    '^.+\\.[tj]s$': ['ts-jest', { tsconfig: '<rootDir>/tsconfig.spec.json' }],
  },
  moduleFileExtensions: ['ts', 'js', 'html'],
  coverageDirectory: '../../coverage/$APP_DIR',
};
APPJEST

        # Create webpack.config.js
        cat > "$APP_DIR/webpack.config.js" << APPWEBPACK
const { NxAppWebpackPlugin } = require('@nx/webpack/app-plugin');
const { join } = require('path');

module.exports = {
  output: {
    path: join(__dirname, '../../dist/$APP_DIR'),
  },
  plugins: [
    new NxAppWebpackPlugin({
      target: 'node',
      compiler: 'tsc',
      main: './src/main.ts',
      tsConfig: './tsconfig.app.json',
      assets: [],
      optimization: false,
      outputHashing: 'none',
      generatePackageJson: true,
    }),
  ],
};
APPWEBPACK

        # Create main.ts for microservice (TCP transport)
        local SERVICE_VAR=$(echo "$APP_NAME" | tr '[:lower:]' '[:upper:]' | tr '-' '_')
        cat > "$APP_DIR/src/main.ts" << APPMAIN
import { Logger } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { MicroserviceOptions, Transport } from '@nestjs/microservices';
import { AppModule } from './app/app.module';

async function bootstrap() {
  const app = await NestFactory.createMicroservice<MicroserviceOptions>(
    AppModule,
    {
      transport: Transport.TCP,
      options: {
        host: process.env.${SERVICE_VAR}_HOST || 'localhost',
        port: parseInt(process.env.${SERVICE_VAR}_PORT, 10) || $APP_PORT,
      },
    },
  );

  await app.listen();
  Logger.log(\`🚀 ${APP_NAME} microservice is running on port $APP_PORT\`);
}

bootstrap();
APPMAIN

        # Create app module
        cat > "$APP_DIR/src/app/app.module.ts" << APPMOD
import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';

@Module({
  imports: [],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
APPMOD

        # Create app controller (for microservice message patterns)
        cat > "$APP_DIR/src/app/app.controller.ts" << APPCTRL
import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @MessagePattern({ cmd: 'ping' })
  ping(@Payload() data: any) {
    return this.appService.ping(data);
  }
}
APPCTRL

        # Create app service
        cat > "$APP_DIR/src/app/app.service.ts" << APPSVC
import { Injectable } from '@nestjs/common';

@Injectable()
export class AppService {
  ping(data: any): { message: string; received: any } {
    return {
      message: 'pong from $APP_NAME',
      received: data,
    };
  }
}
APPSVC

        # Create app controller spec
        cat > "$APP_DIR/src/app/app.controller.spec.ts" << APPSPEC
import { Test, TestingModule } from '@nestjs/testing';
import { AppController } from './app.controller';
import { AppService } from './app.service';

describe('AppController', () => {
  let app: TestingModule;

  beforeAll(async () => {
    app = await Test.createTestingModule({
      controllers: [AppController],
      providers: [AppService],
    }).compile();
  });

  describe('ping', () => {
    it('should return pong', () => {
      const appController = app.get<AppController>(AppController);
      expect(appController.ping({ test: 'data' })).toEqual({
        message: 'pong from $APP_NAME',
        received: { test: 'data' },
      });
    });
  });
});
APPSPEC
    }

    # Create each microservice app
    PORT=3001
    for service in "${SERVICES[@]}"; do
        create_nestjs_app "$service" "$PORT"

        # Create contracts library for this service
        echo -e "  ${CYAN}Creating contracts library for $service...${NC}"

        CONTRACT_DIR="libs/contracts/$service"
        mkdir -p "$CONTRACT_DIR/src/lib"

        # Create project.json for contracts
        cat > "$CONTRACT_DIR/project.json" << CTRPROJ
{
  "name": "contracts-$service",
  "\$schema": "../../../node_modules/nx/schemas/project-schema.json",
  "sourceRoot": "$CONTRACT_DIR/src",
  "projectType": "library",
  "tags": ["type:contracts"],
  "targets": {
    "build": {
      "executor": "@nx/js:tsc",
      "outputs": ["{options.outputPath}"],
      "options": {
        "outputPath": "dist/$CONTRACT_DIR",
        "main": "$CONTRACT_DIR/src/index.ts",
        "tsConfig": "$CONTRACT_DIR/tsconfig.lib.json",
        "assets": []
      }
    }
  }
}
CTRPROJ

        # Create tsconfig files for contracts
        cat > "$CONTRACT_DIR/tsconfig.json" << CTRTS
{
  "extends": "../../../tsconfig.base.json",
  "compilerOptions": {
    "module": "commonjs"
  },
  "files": [],
  "include": [],
  "references": [
    {
      "path": "./tsconfig.lib.json"
    }
  ]
}
CTRTS

        cat > "$CONTRACT_DIR/tsconfig.lib.json" << CTRTSLIB
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "outDir": "../../../dist/out-tsc",
    "declaration": true,
    "types": ["node"]
  },
  "include": ["src/**/*.ts"],
  "exclude": ["src/**/*.spec.ts", "src/**/*.test.ts"]
}
CTRTSLIB

        # Create index.ts
        cat > "$CONTRACT_DIR/src/index.ts" << CTRIDX
// Export DTOs and patterns for $service
export * from './lib/patterns';
export * from './lib/dto';
CTRIDX

        # Create patterns file
        SERVICE_UPPER=$(echo "$service" | tr '[:lower:]' '[:upper:]' | tr '-' '_')
        cat > "$CONTRACT_DIR/src/lib/patterns.ts" << CTRPAT
// Message patterns for $service
export const ${SERVICE_UPPER}_PATTERNS = {
  PING: { cmd: 'ping' },
  // Add more patterns here
};
CTRPAT

        # Create dto file
        cat > "$CONTRACT_DIR/src/lib/dto.ts" << CTRDTO
// DTOs for $service
// Add your DTOs here
CTRDTO

        PORT=$((PORT + 1))
    done

    # Update tsconfig.base.json with contracts path mappings
    python3 -c "
import json
with open('tsconfig.base.json', 'r') as f:
    config = json.load(f)
# Add contracts paths
services = '${SERVICES[*]}'.split()
for svc in services:
    config['compilerOptions']['paths']['@${PROJECT_NAME}/contracts/' + svc] = ['libs/contracts/' + svc + '/src/index.ts']
with open('tsconfig.base.json', 'w') as f:
    json.dump(config, f, indent=2)
"

    echo ""
    echo -e "  ${GREEN}✓${NC} Microservice apps created"
    echo ""
fi

# ═══════════════════════════════════════════════════════════════════════════
# Step 4: Copy Database Entities
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Step 4: Setting Up Database Entities${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Create entities directory in database lib
ENTITIES_SRC="$OUTPUT_DIR/database/entities"
ENTITIES_DEST="$TARGET_DIR/libs/database/src/entities"

if [ -d "$ENTITIES_SRC" ] && [ "$(ls -A "$ENTITIES_SRC" 2>/dev/null)" ]; then
    mkdir -p "$ENTITIES_DEST"
    if ! cp -r "$ENTITIES_SRC"/* "$ENTITIES_DEST/" 2>&1; then
        echo -e "  ${RED}✗${NC} Failed to copy entities from $ENTITIES_SRC to $ENTITIES_DEST"
        exit 1
    fi
    ENTITY_COUNT=$(ls -1 "$ENTITIES_DEST"/*.entity.ts 2>/dev/null | wc -l | tr -d ' ')
    echo -e "  ${GREEN}✓${NC} Copied $ENTITY_COUNT TypeORM entities to libs/database/src/entities/"

    # Create index.ts to export all entities using Python (works in both bash and zsh)
    python3 -c "
import os
entities_dir = '$ENTITIES_DEST'
files = sorted([f for f in os.listdir(entities_dir) if f.endswith('.entity.ts')])
with open(os.path.join(entities_dir, 'index.ts'), 'w') as out:
    out.write('// Auto-generated entity exports\n')
    for f in files:
        name = f.replace('.entity.ts', '')
        out.write(f\"export * from './{name}.entity';\n\")
print(f'  Generated exports for {len(files)} entities')
"
    echo -e "  ${GREEN}✓${NC} Created entity index exports"
else
    echo -e "  ${YELLOW}!${NC} No entities found in $ENTITIES_SRC"
    mkdir -p "$ENTITIES_DEST"
    echo "// Add your TypeORM entities here" > "$ENTITIES_DEST/index.ts"
fi

echo ""

# ═══════════════════════════════════════════════════════════════════════════
# Step 5: Install Additional Dependencies
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Step 5: Installing Dependencies${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ "$SKIP_INSTALL" = false ]; then
    echo -e "  ${CYAN}Installing NestJS packages...${NC}"

    # Use --legacy-peer-deps to avoid peer dependency conflicts
    # Install version-matched packages for NestJS 10.x (what Nx 20.8.0 uses)
    npm install --save --legacy-peer-deps \
        @nestjs/typeorm typeorm mysql2 \
        @nestjs/config \
        @nestjs/jwt @nestjs/passport passport passport-jwt \
        class-validator class-transformer \
        "@nestjs/microservices@^10.0.0" \
        "@nestjs/terminus@^10.0.0" \
        bcrypt uuid \
        2>&1 | grep -E "(added|npm warn|npm error)" || true

    echo -e "  ${CYAN}Installing dev dependencies...${NC}"
    npm install --save-dev --legacy-peer-deps \
        "@nestjs/testing@^10.0.0" \
        @types/passport-jwt @types/bcrypt \
        2>&1 | grep -E "(added|npm warn|npm error)" || true

    echo -e "  ${GREEN}✓${NC} Dependencies installed"
else
    echo -e "  ${YELLOW}!${NC} Skipping npm install (--skip-install)"
    echo ""
    echo -e "  ${CYAN}Run these commands manually:${NC}"
    echo "  cd $TARGET_DIR"
    echo "  npm install --legacy-peer-deps @nestjs/typeorm typeorm mysql2 @nestjs/config"
    echo "  npm install --legacy-peer-deps @nestjs/jwt @nestjs/passport passport passport-jwt"
    echo "  npm install --legacy-peer-deps class-validator class-transformer bcrypt uuid"
    echo "  npm install --legacy-peer-deps @nestjs/microservices@^10.0.0 @nestjs/terminus@^10.0.0"
    echo "  npm install --save-dev --legacy-peer-deps @nestjs/testing@^10.0.0 @types/passport-jwt @types/bcrypt"
fi

echo ""

# ═══════════════════════════════════════════════════════════════════════════
# Step 6: Create Configuration Files
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Step 6: Creating Configuration Files${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Get database name from source project or use default
DB_NAME=$(basename "$SOURCE_PROJECT" 2>/dev/null | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g' || echo "myapp")

# Create .env.example
cat > "$TARGET_DIR/.env.example" << EOF
# Application
NODE_ENV=development
PORT=3000

# Database
DB_HOST=localhost
DB_PORT=3306
DB_USERNAME=root
DB_PASSWORD=
DB_DATABASE=${DB_NAME}

# JWT
JWT_SECRET=your-secret-key-change-in-production
JWT_EXPIRES_IN=1d

# Redis (if using)
REDIS_HOST=localhost
REDIS_PORT=6379
EOF

# Add microservice ports if services exist
if [ ${#SERVICES[@]} -gt 0 ]; then
    echo "" >> "$TARGET_DIR/.env.example"
    echo "# Microservices" >> "$TARGET_DIR/.env.example"
    PORT=3001
    for service in "${SERVICES[@]}"; do
        SERVICE_VAR=$(echo "$service" | tr '[:lower:]' '[:upper:]' | tr '-' '_')
        echo "${SERVICE_VAR}_HOST=localhost" >> "$TARGET_DIR/.env.example"
        echo "${SERVICE_VAR}_PORT=$PORT" >> "$TARGET_DIR/.env.example"
        PORT=$((PORT + 1))
    done
fi

echo -e "  ${GREEN}✓${NC} Created .env.example"

# Create .env from .env.example (ready to use for development)
cp "$TARGET_DIR/.env.example" "$TARGET_DIR/.env"
# Generate a random JWT secret for development
JWT_SECRET=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null)
if [ -z "$JWT_SECRET" ]; then
    echo -e "  ${RED}✗${NC} Failed to generate JWT secret (neither openssl nor python3 available)"
    exit 1
fi
# Try GNU sed first, then BSD sed (macOS)
if ! sed -i.bak "s/your-secret-key-change-in-production/$JWT_SECRET/" "$TARGET_DIR/.env" 2>/dev/null; then
    if ! sed -i '' "s/your-secret-key-change-in-production/$JWT_SECRET/" "$TARGET_DIR/.env" 2>/dev/null; then
        echo -e "  ${YELLOW}!${NC} Warning: Could not update JWT_SECRET in .env - please set manually"
    fi
fi
rm -f "$TARGET_DIR/.env.bak" 2>/dev/null || true
echo -e "  ${GREEN}✓${NC} Created .env with generated JWT secret"

# Create database config in libs/database
mkdir -p "$TARGET_DIR/libs/database/src/config"
cat > "$TARGET_DIR/libs/database/src/config/database.config.ts" << 'EOF'
import { registerAs } from '@nestjs/config';

export default registerAs('database', () => ({
  type: 'mysql' as const,
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT, 10) || 3306,
  username: process.env.DB_USERNAME || 'root',
  password: process.env.DB_PASSWORD || '',
  database: process.env.DB_DATABASE || 'myapp',
  entities: [__dirname + '/../entities/*.entity{.ts,.js}'],
  synchronize: process.env.NODE_ENV !== 'production',
  logging: process.env.NODE_ENV === 'development',
}));
EOF

echo -e "  ${GREEN}✓${NC} Created database configuration"

# Update database lib index
cat > "$TARGET_DIR/libs/database/src/index.ts" << 'EOF'
export * from './entities';
export { default as databaseConfig } from './config/database.config';
export * from './lib/database.module';
EOF

echo -e "  ${GREEN}✓${NC} Updated database library exports"

# Copy migration analysis reference
mkdir -p "$TARGET_DIR/docs/migration"
DOCS_COPIED=0
DOCS_FAILED=0
for doc_file in "architecture_context.json" "legacy_analysis.json" "routes.json" "ARCHITECTURE.md" "NESTJS_BEST_PRACTICES.md"; do
    if [ -f "$OUTPUT_DIR/analysis/$doc_file" ]; then
        if cp "$OUTPUT_DIR/analysis/$doc_file" "$TARGET_DIR/docs/migration/" 2>&1; then
            DOCS_COPIED=$((DOCS_COPIED + 1))
        else
            echo -e "  ${YELLOW}!${NC} Warning: Failed to copy $doc_file"
            DOCS_FAILED=$((DOCS_FAILED + 1))
        fi
    fi
done
if [ $DOCS_COPIED -gt 0 ]; then
    echo -e "  ${GREEN}✓${NC} Copied $DOCS_COPIED migration analysis files to docs/migration/"
fi
if [ $DOCS_FAILED -gt 0 ]; then
    echo -e "  ${YELLOW}!${NC} Warning: $DOCS_FAILED files failed to copy"
fi

# Add .env to .gitignore if not already there
if ! grep -q "^\.env$" "$TARGET_DIR/.gitignore" 2>/dev/null; then
    echo "" >> "$TARGET_DIR/.gitignore"
    echo "# Environment files" >> "$TARGET_DIR/.gitignore"
    echo ".env" >> "$TARGET_DIR/.gitignore"
    echo ".env.local" >> "$TARGET_DIR/.gitignore"
    echo -e "  ${GREEN}✓${NC} Added .env to .gitignore"
fi

echo ""

# ═══════════════════════════════════════════════════════════════════════════
# Step 7: Configure Gateway App
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Step 7: Configuring Gateway App${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Create gateway config directory
mkdir -p "$TARGET_DIR/apps/gateway/src/config"

# Create configuration file for gateway
cat > "$TARGET_DIR/apps/gateway/src/config/configuration.ts" << 'EOF'
export default () => ({
  port: parseInt(process.env.PORT, 10) || 3000,
  database: {
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT, 10) || 3306,
    username: process.env.DB_USERNAME || 'root',
    password: process.env.DB_PASSWORD || '',
    database: process.env.DB_DATABASE || 'myapp',
  },
  jwt: {
    secret: process.env.JWT_SECRET,
    expiresIn: process.env.JWT_EXPIRES_IN || '1d',
  },
  redis: {
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT, 10) || 6379,
  },
});
EOF

echo -e "  ${GREEN}✓${NC} Created gateway configuration"

# Update gateway main.ts with validation pipe and config
cat > "$TARGET_DIR/apps/gateway/src/main.ts" << 'EOF'
import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { AppModule } from './app/app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Global prefix for all routes
  app.setGlobalPrefix('api');

  // Global validation pipe
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
      transformOptions: {
        enableImplicitConversion: true,
      },
    }),
  );

  // Enable CORS
  app.enableCors({
    origin: process.env.CORS_ORIGINS?.split(',') || '*',
    credentials: true,
  });

  const port = process.env.PORT || 3000;
  await app.listen(port);
  console.log(`🚀 Gateway is running on: http://localhost:${port}/api`);
}
bootstrap();
EOF

echo -e "  ${GREEN}✓${NC} Updated gateway main.ts with validation and CORS"

# Update gateway app.module.ts with ConfigModule
cat > "$TARGET_DIR/apps/gateway/src/app/app.module.ts" << 'EOF'
import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import configuration from '../config/configuration';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      load: [configuration],
      envFilePath: ['.env.local', '.env'],
    }),
    // TODO: Add TypeOrmModule.forRootAsync() here
    // TODO: Add your feature modules here
  ],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
EOF

echo -e "  ${GREEN}✓${NC} Updated gateway app.module.ts with ConfigModule"

echo ""

# ═══════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  ${GREEN}Nx Workspace Created Successfully!${NC}                                      ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Workspace:${NC} $TARGET_DIR"
echo ""
echo -e "${BLUE}Structure:${NC}"
echo "  apps/"
echo "    └── gateway/              # Main HTTP API (port 3000)"
for service in "${SERVICES[@]}"; do
    echo "    └── $service/"
done
echo "  libs/"
echo "    ├── shared-dto/           # Shared DTOs and interfaces"
echo "    ├── database/             # TypeORM config and entities"
echo "    ├── common/               # Shared utilities"
if [ ${#SERVICES[@]} -gt 0 ]; then
    echo "    └── contracts/            # Service contracts (per microservice)"
fi
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "  ✓ .env file created with generated JWT secret"
echo "  ✓ Database configuration ready"
echo "  ✓ Validation pipe configured"
echo "  ✓ CORS enabled"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "  1. Navigate to workspace:"
echo -e "     ${CYAN}cd $TARGET_DIR${NC}"
echo ""
echo "  2. Configure your database in .env:"
echo -e "     ${CYAN}DB_HOST=your-db-host${NC}"
echo -e "     ${CYAN}DB_DATABASE=your-db-name${NC}"
echo -e "     ${CYAN}DB_PASSWORD=your-password${NC}"
echo ""
echo "  3. Start development server:"
echo -e "     ${CYAN}npx nx serve gateway${NC}"
echo ""
echo "  4. View Nx project graph:"
echo -e "     ${CYAN}npx nx graph${NC}"
echo ""
echo "  5. Migrate services using Ralph Wiggum (inside Claude Code):"
echo -e "     ${CYAN}/ralph-wiggum:ralph-loop \"\$(cat prompts/legacy_php_migration.md)\" --completion-promise \"SERVICE_COMPLETE\" --max-iterations 60${NC}"
echo ""
if [ ${#SERVICES[@]} -gt 0 ]; then
    echo "  6. For each extracted microservice (inside Claude Code):"
    echo -e "     ${CYAN}/ralph-wiggum:ralph-loop \"\$(cat prompts/extract_service.md)\" --completion-promise \"SERVICE_COMPLETE\" --max-iterations 60${NC}"
    echo ""
fi
echo -e "${GREEN}Happy migrating!${NC}"
echo ""
