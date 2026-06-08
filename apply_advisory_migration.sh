#!/bin/bash

echo "🔄 Applying advisory system restructure migration..."
echo ""

# Apply the restructure migration
docker compose exec -T db psql -U bee_user -d bee_db < migrations/restructure_advisory_system.sql

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Migration completed successfully!"
    echo ""
    echo "🔄 Restarting API container..."
    docker compose restart api
    echo ""
    echo "✅ Done! API should now start without errors."
    echo ""
    echo "📝 Next steps:"
    echo "   1. Seed advisory templates and actions using the admin panel or API"
    echo "   2. Use: POST /advisory-templates to create classifications"
    echo "   3. Use: POST /advisory-library to add actions for each classification"
    echo ""
else
    echo ""
    echo "❌ Migration failed!"
    echo "Check the error messages above."
fi
