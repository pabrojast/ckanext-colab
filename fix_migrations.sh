#!/bin/bash

# Script para limpiar y aplicar migraciones de CKAN colab
# Ejecutar este script en el pod de CKAN

echo "🔧 Limpiando estado de migración de colab..."

# Conectar a PostgreSQL y limpiar el estado de Alembic
python3 << EOF
import os
import psycopg2
from urllib.parse import urlparse

# Obtener URL de base de datos desde variable de entorno o archivo de configuración
db_url = os.environ.get('CKAN_SQLALCHEMY_URL', 'postgresql://ckan_default:password@postgres/ckan_default')

# Parsear URL de base de datos
parsed = urlparse(db_url)

try:
    # Conectar a la base de datos
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path[1:],  # Remover el '/' inicial
        user=parsed.username,
        password=parsed.password
    )
    
    conn.autocommit = True
    cursor = conn.cursor()
    
    print("✅ Conectado a la base de datos")
    
    # Verificar si la tabla colab_alembic_version existe
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'colab_alembic_version'
        );
    """)
    
    table_exists = cursor.fetchone()[0]
    
    if table_exists:
        print("📋 Tabla colab_alembic_version encontrada")
        
        # Verificar estado actual
        cursor.execute("SELECT version_num FROM colab_alembic_version;")
        current_version = cursor.fetchone()
        
        if current_version:
            print(f"📌 Versión actual: {current_version[0]}")
            
            # Si la versión es una de las problemáticas, resetear a la última buena
            if current_version[0] in ['f3d4e5a6b7c8', 'd7e8f9a1b2c3']:
                print("🔄 Reseteando a versión estable bc416bb48b61...")
                cursor.execute("UPDATE colab_alembic_version SET version_num = 'bc416bb48b61';")
                print("✅ Versión reseteada exitosamente")
            else:
                print("✅ Versión actual es estable")
        else:
            print("⚠️ No hay versión registrada, estableciendo versión base...")
            cursor.execute("INSERT INTO colab_alembic_version (version_num) VALUES ('bc416bb48b61');")
    else:
        print("📋 Creando tabla colab_alembic_version...")
        cursor.execute("""
            CREATE TABLE colab_alembic_version (
                version_num VARCHAR(32) NOT NULL,
                CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
            );
        """)
        cursor.execute("INSERT INTO colab_alembic_version (version_num) VALUES ('bc416bb48b61');")
        print("✅ Tabla creada y versión base establecida")
    
    # Verificar si la columna citizens4water ya existe
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = 'colab' AND column_name = 'citizens4water'
        );
    """)
    
    column_exists = cursor.fetchone()[0]
    
    if column_exists:
        print("🌊 La columna citizens4water ya existe")
        # Si la columna ya existe, marcar la migración como aplicada
        cursor.execute("UPDATE colab_alembic_version SET version_num = 'e8f9a0b1c2d4';")
        print("✅ Migración marcada como aplicada")
    else:
        print("🌊 La columna citizens4water no existe, se agregará en la migración")
    
    # Verificar si la tabla colab_organization_requests existe
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'colab_organization_requests'
        );
    """)
    
    org_table_exists = cursor.fetchone()[0]
    print(f"🏢 Tabla colab_organization_requests existe: {org_table_exists}")
    
    cursor.close()
    conn.close()
    
    print("🎉 Limpieza completada exitosamente")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("Puedes intentar ejecutar las siguientes consultas SQL manualmente:")
    print("UPDATE colab_alembic_version SET version_num = 'bc416bb48b61';")
    print("-- O si no existe la tabla:")
    print("CREATE TABLE colab_alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY);")
    print("INSERT INTO colab_alembic_version (version_num) VALUES ('bc416bb48b61');")

EOF

echo ""
echo "🚀 Ejecutando migraciones de colab..."
ckan -c /srv/app/production.ini db upgrade --plugin colab

echo ""
echo "✅ ¡Proceso completado!"
