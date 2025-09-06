/**
 * WorkflowApproval Component
 * Handles wait node approvals and user actions for n8n workflows
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Button,
  TextField,
  Typography,
  Box,
  Alert,
  CircularProgress,
  Collapse,
  Divider,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  CheckCircle,
  Cancel,
  Edit,
  ExpandMore,
  ExpandLess,
  Info,
  Warning,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { 
  WaitNodeData, 
  WaitNodeAction, 
  WaitNodeField,
  Message,
  MessageCategory,
  isWaitingMessage 
} from '../types/unified';
import { workflowAPI } from '../services/workflowAPI';

interface WorkflowApprovalProps {
  message: Message;
  sessionId: string;
  onActionComplete?: (action: string, success: boolean) => void;
}

export const WorkflowApproval: React.FC<WorkflowApprovalProps> = ({
  message,
  sessionId,
  onActionComplete,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [currentAction, setCurrentAction] = useState<WaitNodeAction | null>(null);
  const [inputValues, setInputValues] = useState<Record<string, any>>({});

  // Extract wait node data
  const waitNode = message.waitNode;
  if (!waitNode || !isWaitingMessage(message)) {
    return null;
  }

  const handleAction = async (action: WaitNodeAction) => {
    if (action.requiresInput) {
      setCurrentAction(action);
      setDialogOpen(true);
      // Initialize input values
      const initialValues: Record<string, any> = {};
      action.inputFields?.forEach(field => {
        initialValues[field.name] = field.defaultValue || '';
      });
      setInputValues(initialValues);
    } else {
      await executeAction(action);
    }
  };

  const executeAction = async (action: WaitNodeAction, additionalData?: Record<string, any>) => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await workflowAPI.handleApproval({
        sessionId,
        action: action.payload.action,
        feedback: additionalData?.feedback || inputValues.feedback,
        modifications: additionalData?.modifications || inputValues.modifications,
        resumeUrl: waitNode.resumeUrl,
      });

      if (response.success) {
        setSuccess(`Successfully ${action.payload.action}ed the workflow`);
        onActionComplete?.(action.payload.action, true);
      } else {
        throw new Error(response.error || 'Action failed');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to complete action');
      onActionComplete?.(action.payload.action, false);
    } finally {
      setLoading(false);
      setDialogOpen(false);
      setCurrentAction(null);
      setInputValues({});
    }
  };

  const renderFieldInput = (field: WaitNodeField) => {
    const value = inputValues[field.name] || '';
    
    switch (field.type) {
      case 'textarea':
        return (
          <TextField
            key={field.name}
            label={field.label}
            name={field.name}
            value={value}
            onChange={(e) => setInputValues({
              ...inputValues,
              [field.name]: e.target.value
            })}
            multiline
            rows={4}
            fullWidth
            required={field.required}
            margin="normal"
            disabled={loading}
          />
        );
      
      case 'select':
        return (
          <TextField
            key={field.name}
            select
            label={field.label}
            name={field.name}
            value={value}
            onChange={(e) => setInputValues({
              ...inputValues,
              [field.name]: e.target.value
            })}
            fullWidth
            required={field.required}
            margin="normal"
            disabled={loading}
            SelectProps={{
              native: true,
            }}
          >
            <option value="">Select...</option>
            {field.options?.map(option => (
              <option key={option} value={option}>{option}</option>
            ))}
          </TextField>
        );
      
      default:
        return (
          <TextField
            key={field.name}
            label={field.label}
            name={field.name}
            type={field.type === 'number' ? 'number' : 'text'}
            value={value}
            onChange={(e) => setInputValues({
              ...inputValues,
              [field.name]: e.target.value
            })}
            fullWidth
            required={field.required}
            margin="normal"
            disabled={loading}
          />
        );
    }
  };

  const renderDisplayData = () => {
    const displayData = waitNode.displayData?.data;
    if (!displayData) return null;

    return (
      <Box sx={{ mt: 2 }}>
        {displayData.extractedText && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Extracted Text
            </Typography>
            <Box 
              sx={{ 
                p: 2, 
                bgcolor: 'grey.50', 
                borderRadius: 1,
                maxHeight: 200,
                overflow: 'auto'
              }}
            >
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                {displayData.extractedText}
              </Typography>
            </Box>
          </Box>
        )}

        {displayData.analysis && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Analysis Results
            </Typography>
            <Box sx={{ p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
              {typeof displayData.analysis === 'object' ? (
                <pre style={{ margin: 0, fontSize: '0.875rem' }}>
                  {JSON.stringify(displayData.analysis, null, 2)}
                </pre>
              ) : (
                <Typography variant="body2">
                  {displayData.analysis}
                </Typography>
              )}
            </Box>
          </Box>
        )}

        {displayData.recommendations && Array.isArray(displayData.recommendations) && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Recommendations
            </Typography>
            {displayData.recommendations.map((rec: any, idx: number) => (
              <Alert 
                key={idx} 
                severity={rec.severity || 'info'} 
                sx={{ mb: 1 }}
              >
                {rec.message || rec}
              </Alert>
            ))}
          </Box>
        )}

        {displayData.hvacComponents && Array.isArray(displayData.hvacComponents) && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              HVAC Components Found
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {displayData.hvacComponents.map((comp: any, idx: number) => (
                <Chip
                  key={idx}
                  label={`${comp.type}: ${comp.name}`}
                  variant="outlined"
                  size="small"
                />
              ))}
            </Box>
          </Box>
        )}
      </Box>
    );
  };

  const getActionIcon = (actionType: string) => {
    switch (actionType) {
      case 'approve':
        return <CheckCircle />;
      case 'reject':
        return <Cancel />;
      case 'modify':
        return <Edit />;
      default:
        return null;
    }
  };

  const getActionColor = (actionType: string): 'primary' | 'error' | 'secondary' | 'inherit' => {
    switch (actionType) {
      case 'primary':
        return 'primary';
      case 'danger':
        return 'error';
      case 'secondary':
        return 'secondary';
      default:
        return 'inherit';
    }
  };

  return (
    <>
      <Card sx={{ mb: 2, borderLeft: 4, borderColor: 'warning.main' }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Warning sx={{ mr: 1, color: 'warning.main' }} />
            <Typography variant="h6" component="div">
              {waitNode.displayData?.title || waitNode.nodeName}
            </Typography>
            <Box sx={{ flexGrow: 1 }} />
            <IconButton
              size="small"
              onClick={() => setExpanded(!expanded)}
              aria-label={expanded ? 'collapse' : 'expand'}
            >
              {expanded ? <ExpandLess /> : <ExpandMore />}
            </IconButton>
          </Box>

          {waitNode.displayData?.description && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {waitNode.displayData.description}
            </Typography>
          )}

          <Collapse in={expanded}>
            {renderDisplayData()}
          </Collapse>

          {error && (
            <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          {success && (
            <Alert severity="success" sx={{ mt: 2 }} onClose={() => setSuccess(null)}>
              {success}
            </Alert>
          )}
        </CardContent>

        <Divider />

        <CardActions sx={{ justifyContent: 'flex-end', p: 2 }}>
          {waitNode.displayData?.actions.map((action) => (
            <Button
              key={action.id}
              variant={action.type === 'primary' ? 'contained' : 'outlined'}
              color={getActionColor(action.type)}
              startIcon={getActionIcon(action.payload.action)}
              onClick={() => handleAction(action)}
              disabled={loading || !!success}
            >
              {loading && currentAction?.id === action.id ? (
                <CircularProgress size={20} />
              ) : (
                action.label
              )}
            </Button>
          ))}
        </CardActions>
      </Card>

      {/* Input Dialog */}
      <Dialog 
        open={dialogOpen} 
        onClose={() => !loading && setDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          {currentAction?.label}
        </DialogTitle>
        <DialogContent>
          {currentAction?.inputFields?.map(field => renderFieldInput(field))}
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => setDialogOpen(false)} 
            disabled={loading}
          >
            Cancel
          </Button>
          <Button 
            onClick={() => currentAction && executeAction(currentAction)}
            variant="contained"
            disabled={loading}
          >
            {loading ? <CircularProgress size={20} /> : 'Submit'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
