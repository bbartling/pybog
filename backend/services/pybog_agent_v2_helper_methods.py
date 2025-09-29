    async def _send_assistant_message(self, session_id: str, content: str) -> None:
        """Send an assistant message via WebSocket."""
        await self.event_bus.publish(
            session_id,
            Event(
                type="chat",
                session_id=session_id,
                operation="chat",
                data={
                    "content": content,
                    "is_complete": True,
                    "message_type": "assistant"
                }
            )
        )

        # Also save to database
        try:
            await self._save_message_to_db(session_id, "assistant", content, {"automated": True})
        except Exception as e:
            logger.error(f"Failed to save automated message to database: {e}")

    async def _send_analysis_results(self, session_id: str, analysis_result: dict, filename: str) -> None:
        """Send formatted analysis results to the user."""
        try:
            # Format the analysis results nicely
            io_points = analysis_result.get("io_points", [])
            control_blocks = analysis_result.get("control_blocks", [])
            quality_score = analysis_result.get("quality_score", 0)

            result_message = f"""## 📊 Analysis Complete for {filename}

**Quality Score:** {quality_score:.1%}

### 🔌 I/O Points ({len(io_points)} found)
"""
            for point in io_points[:5]:  # Show first 5
                result_message += f"- **{point['name']}** ({point['type']}): {point['description']}\n"

            if len(io_points) > 5:
                result_message += f"- ... and {len(io_points) - 5} more points\n"

            result_message += f"\n### ⚙️ Control Blocks ({len(control_blocks)} found)\n"
            for block in control_blocks[:3]:  # Show first 3
                result_message += f"- **{block['name']}** ({block['type']}): {block['description']}\n"

            if len(control_blocks) > 3:
                result_message += f"- ... and {len(control_blocks) - 3} more blocks\n"

            result_message += "\n✅ Analysis complete! You can now request BOG file generation."

            await self._send_assistant_message(session_id, result_message)

        except Exception as e:
            logger.error(f"Error sending analysis results: {e}")
            await self._send_assistant_message(
                session_id,
                f"Analysis completed, but I had trouble formatting the results: {str(e)}"
            )