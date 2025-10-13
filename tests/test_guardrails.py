"""
Tests pour les output guardrails
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from company_agents.guardrails.eclaireur import eclaireur_output_guardrail
from company_agents.metrics.agent_wrappers import run_agent_with_metrics
from agents import GuardrailFunctionOutput


class TestEclaireurGuardrail:
    """Tests du guardrail de l'Éclaireur"""

    @pytest.mark.asyncio
    async def test_url_mode_missing_target_domain(self):
        """Vérifie que le guardrail déclenche si target_domain manquant en MODE URL"""
        ctx = {"original_input": "https://www.agencenile.com/"}
        agent = Mock()
        output = {
            "entity_legal_name": "Nile",
            "target_domain": None,  # Manquant !
            "sources": [],
        }

        result = await eclaireur_output_guardrail(ctx, agent, output)

        assert isinstance(result, GuardrailFunctionOutput)
        assert result.tripwire_triggered is True
        assert "target_domain manquant" in str(result.output_info.get("violations", []))

    @pytest.mark.asyncio
    async def test_url_mode_no_ondomain_source(self):
        """Vérifie que le guardrail déclenche si aucune source on-domain"""
        ctx = {"original_input": "https://www.agencenile.com/"}
        agent = Mock()
        output = {
            "entity_legal_name": "Nile",
            "target_domain": "agencenile.com",
            "sources": [
                {
                    "url": "https://www.societe.com/nile",  # Pas on-domain
                    "accessibility": "ok",
                }
            ],
        }

        result = await eclaireur_output_guardrail(ctx, agent, output)

        assert isinstance(result, GuardrailFunctionOutput)
        assert result.tripwire_triggered is True
        assert "Aucune source on-domain" in str(result.output_info.get("violations", []))

    @pytest.mark.asyncio
    async def test_dead_links_detected(self):
        """Vérifie que le guardrail détecte les liens morts"""
        ctx = {"original_input": "https://www.agencenile.com/"}
        agent = Mock()
        output = {
            "entity_legal_name": "Nile",
            "target_domain": "agencenile.com",
            "sources": [
                {
                    "url": "https://www.agencenile.com/mentions-legales",
                    "accessibility": "404",  # Lien mort
                },
                {
                    "url": "https://www.agencenile.com/contact",
                    "accessibility": "ok",
                },
            ],
        }

        result = await eclaireur_output_guardrail(ctx, agent, output)

        assert isinstance(result, GuardrailFunctionOutput)
        assert result.tripwire_triggered is True
        assert "URLs inaccessibles" in str(result.output_info.get("violations", []))
        assert "https://www.agencenile.com/mentions-legales" in result.output_info.get(
            "removed_dead_links", []
        )

    @pytest.mark.asyncio
    async def test_valid_output(self):
        """Vérifie que le guardrail laisse passer une sortie valide"""
        ctx = {"original_input": "https://www.agencenile.com/"}
        agent = Mock()
        output = {
            "entity_legal_name": "Nile",
            "target_domain": "agencenile.com",
            "sources": [
                {
                    "url": "https://www.agencenile.com/mentions-legales",
                    "accessibility": "ok",
                },
                {
                    "url": "https://www.agencenile.com/contact",
                    "accessibility": "ok",
                },
            ],
        }

        result = await eclaireur_output_guardrail(ctx, agent, output)

        assert isinstance(result, GuardrailFunctionOutput)
        assert result.tripwire_triggered is False
        assert result.output_info.get("status") == "ok"

    @pytest.mark.asyncio
    async def test_name_mode_no_target_domain_required(self):
        """Vérifie que target_domain n'est pas requis en MODE NOM"""
        ctx = {"original_input": "Nile"}  # Pas d'URL
        agent = Mock()
        output = {
            "entity_legal_name": "Nile",
            "target_domain": None,  # OK en MODE NOM
            "sources": [
                {"url": "https://www.societe.com/nile", "accessibility": "ok"}
            ],
        }

        result = await eclaireur_output_guardrail(ctx, agent, output)

        assert isinstance(result, GuardrailFunctionOutput)
        assert result.tripwire_triggered is False

    @pytest.mark.asyncio
    async def test_guardrail_error_does_not_block(self):
        """Vérifie qu'une erreur interne du guardrail ne bloque pas l'agent"""
        ctx = {}  # Contexte invalide pour forcer une erreur
        agent = Mock()
        output = None  # Output invalide

        result = await eclaireur_output_guardrail(ctx, agent, output)

        # Le guardrail doit retourner tripwire_triggered=False en cas d'erreur
        assert isinstance(result, GuardrailFunctionOutput)
        assert result.tripwire_triggered is False
        assert "error" in result.output_info


class TestRetryMechanism:
    """Tests du mécanisme de retry"""

    @pytest.mark.asyncio
    async def test_retry_on_guardrail_tripwire(self):
        """Vérifie que le retry est déclenché quand le guardrail échoue"""
        # Mock de l'agent
        mock_agent = Mock()
        mock_agent.hooks = None

        # Mock du Runner.run
        from agents import Runner
        from agents.exceptions import OutputGuardrailTripwireTriggered

        # Simuler : 1ère tentative = échec, 2ème = succès
        call_count = 0

        async def mock_run(agent, input, max_turns):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # 1ère tentative : guardrail déclenché
                mock_result = Mock()
                mock_result.output_info = {
                    "violations": ["test violation"],
                    "removed_dead_links": ["https://dead.link"],
                }
                raise OutputGuardrailTripwireTriggered(result=mock_result)
            else:
                # 2ème tentative : succès
                mock_result = Mock()
                mock_result.final_output = {"test": "success"}
                return mock_result

        # Mock status_manager
        mock_status_manager = AsyncMock()
        mock_status_manager.update_agent_status_detailed = AsyncMock()

        # Exécuter le wrapper (avec monkey patch)
        original_run = Runner.run
        Runner.run = mock_run

        try:
            result = await run_agent_with_metrics(
                agent=mock_agent,
                agent_name="Test Agent",
                session_id="test-session",
                input_data="test input",
                status_manager=mock_status_manager,
                max_turns=3,
                max_retries=2,
            )

            # Vérifier que 2 tentatives ont été faites
            assert call_count == 2
            assert result["status"] == "success"
            assert result["result"].final_output == {"test": "success"}

        finally:
            Runner.run = original_run


if __name__ == "__main__":
    # Exécuter les tests
    pytest.main([__file__, "-v"])

