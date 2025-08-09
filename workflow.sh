#!/bin/bash
# Non-interactive workflow for Claude Code

if [ -z "$1" ]; then
    echo "Usage: ./workflow.sh \"Your development task\""
    echo "Example: ./workflow.sh \"Add user authentication with JWT\""
    exit 1
fi

TASK="$1"

echo "🚀 AI Development Workflow"
echo "========================"
echo "📋 Task: $TASK"
echo ""

# Ensure we're in the right directory
cd "$(dirname "$0")"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "📝 Copy .env.template to .env and add your API keys:"
    echo "   cp .env.template .env"
    echo "   # Then edit .env with your real API keys"
    exit 1
fi

# Load environment
source .env

# Validate API keys exist
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your-openai-api-key-here" ]; then
    echo "❌ OPENAI_API_KEY not set properly in .env"
    exit 1
fi

if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "your-anthropic-api-key-here" ]; then
    echo "❌ ANTHROPIC_API_KEY not set properly in .env"
    exit 1
fi

export OPENAI_API_KEY
export ANTHROPIC_API_KEY

# Step 1: Generate specification
echo "1️⃣ Generating specification..."
python3 aidev.py spec "$TASK"

if [ ! -f "aidev_spec.json" ]; then
    echo "❌ Failed to generate specification"
    exit 1
fi

echo ""
echo "📄 Generated Spec:"
cat aidev_spec.json | python3 -m json.tool | head -20
echo ""

# Step 2: Implement
echo "2️⃣ Implementing solution..."
python3 aidev.py implement

# Step 3: Review
echo ""
echo "3️⃣ Reviewing implementation..."
python3 aidev.py review

# Step 4: Show changes
echo ""
echo "4️⃣ Changes made:"
python3 aidev.py patch

echo ""
echo "✅ Workflow complete!"
echo ""
echo "To apply changes run:"
echo "  python3 aidev.py patch --apply"
echo "  git commit -m \"AI: $TASK\""
